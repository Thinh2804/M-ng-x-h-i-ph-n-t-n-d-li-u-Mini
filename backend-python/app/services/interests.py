"""Sở thích theo nội dung bài viết (Neo4j) - gợi ý kết bạn cho cả user mới chưa có bạn.

Khi user đăng / xem / thích / bình luận một bài, từ khóa của bài được ghi thành
    (:User)-[:INTERESTED_IN {weight}]->(:Keyword {name})
Hai user có chung từ khóa → gợi ý kết bạn cho nhau (truy vấn đối xứng nên "ngược lại" tự đúng).
Từ khóa càng hiếm (ít user quan tâm) thì càng có giá trị, giống IDF.
"""
import re
import uuid
import logging
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone

from pymongo.errors import PyMongoError
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from .. import database as dbx

log = logging.getLogger("interests")

# Trọng số theo mức độ quan tâm
WEIGHT_POST = 2.0     # tự viết bài
WEIGHT_COMMENT = 1.5  # bình luận
WEIGHT_LIKE = 1.0     # thích
WEIGHT_VIEW = 1.0     # mở xem bài

MAX_KEYWORDS = 20

# Từ phổ biến không mang chủ đề (tiếng Việt + câu mẫu "Hôm nay mình ..., mọi người thấy sao?")
STOPWORDS = set("""
hôm nay mai qua mình tôi tớ tao mày bạn các những mọi người ai gì nào đâu sao thế vậy
là và với của có không chưa được bị cho này kia đó đấy ấy một hai ba cái con chiếc
thì mà nên vì nếu nhưng hay hoặc cũng vẫn đã đang sẽ vừa mới còn nữa chỉ cùng theo
rất quá lắm hơn nhất nhiều ít thật luôn thấy biết muốn cần phải làm đi đến về ra vào
lên xuống ở tại trong ngoài trên dưới từ để khi lúc rồi nhé nha nhỉ ạ ơi à ừ ok oke
chúng ta họ nó em anh chị ông bà bác cô chú thôi đây kìa vậy thế
test thử hihi haha hehe
""".split())

_TOKEN = re.compile(r"\w+", re.UNICODE)


def extract_keywords(text: str) -> list[str]:
    """Từ khóa = từ đơn có nghĩa + cụm 2 từ liền nhau (vd. 'đà lạt', 'đồ án')."""
    text = unicodedata.normalize("NFC", (text or "").lower())
    tokens = [t for t in _TOKEN.findall(text) if not t.isdigit()]
    keep = [t if (t not in STOPWORDS and len(t) >= 2) else None for t in tokens]
    words = [t for t in keep if t]
    bigrams = [f"{a} {b}" for a, b in zip(keep, keep[1:]) if a and b]
    out = list(dict.fromkeys(bigrams + words))  # bỏ trùng, giữ thứ tự, ưu tiên cụm từ
    return out[:MAX_KEYWORDS]


_MERGE = """
MATCH (u:User {id: $user_id})
UNWIND $keywords AS kw
MERGE (k:Keyword {name: kw})
MERGE (u)-[r:INTERESTED_IN]->(k)
ON CREATE SET r.weight = 0.0
SET r.weight = r.weight + $weight, r.updated_at = datetime()
"""


def ensure_schema():
    with dbx.neo4j_driver.session() as s:
        s.run("CREATE CONSTRAINT keyword_name IF NOT EXISTS FOR (k:Keyword) REQUIRE k.name IS UNIQUE")


# Cạnh trực tiếp giữa 2 user có nội dung trùng khớp (vô hướng: cả 2 phía đều thấy nhau)
_LINK = """
MATCH (u:User {id: $user_id}), (o:User {id: $other_id})
WHERE u <> o
MERGE (u)-[m:CONTENT_MATCH]-(o)
ON CREATE SET m.score = 0.0
SET m.score = m.score + $weight, m.topics = $topics, m.updated_at = datetime()
"""

# Người đăng bài mới khớp nhất: những user quan tâm nhiều nhất tới các từ khóa của bài
_TOP_MATCHES = """
MATCH (k:Keyword)<-[r:INTERESTED_IN]-(o:User)
WHERE k.name IN $keywords AND o.id <> $user_id
WITH o, k, log(1.0 + r.weight) / log(1.0 + COUNT { (k)<-[:INTERESTED_IN]-() }) AS s
WITH o, sum(s) AS score
RETURN o.id AS id ORDER BY score DESC LIMIT $limit
"""
TOP_MATCHES_ON_POST = 5



def write_interest(user_id: str, keywords: list[str], weight: float,
                   target_id: str | None = None, find_matches: bool = False):
    """Ghi trực tiếp vào Neo4j (dùng chung cho API và outbox worker).

    target_id: tác giả bài được xem/thích/bình luận → nối CONTENT_MATCH với người đó.
    find_matches: user vừa đăng bài → nối CONTENT_MATCH với những người khớp nội dung nhất.
    """
    topics = keywords  # toàn bộ từ khóa của bài; display_topics() chọn cụm để hiển thị
    with dbx.neo4j_driver.session() as s:
        if find_matches:  # tìm trước khi ghi để không tự so với chính bài vừa đăng
            targets = [r["id"] for r in s.run(_TOP_MATCHES, keywords=keywords, user_id=user_id,
                                               limit=TOP_MATCHES_ON_POST)]
        else:
            targets = [target_id] if target_id and target_id != user_id else []
        s.run(_MERGE, user_id=user_id, keywords=keywords, weight=float(weight))
        for other in targets:
            s.run(_LINK, user_id=user_id, other_id=other, weight=float(weight), topics=topics)


def record_interest(user_id: str | None, text: str, weight: float, source: str,
                    target_id: str | None = None) -> list[str]:
    """Ghi sở thích; Neo4j lỗi thì đưa vào outbox để worker ghi lại sau. Không bao giờ raise."""
    keywords = extract_keywords(text)
    if not user_id or not keywords:
        return keywords
    find_matches = source == "post"
    try:
        write_interest(user_id, keywords, weight, target_id, find_matches)
    except (Neo4jError, ServiceUnavailable, OSError) as e:
        try:
            dbx.db.outbox.insert_one({
                "_id": str(uuid.uuid4()), "type": "record_interest",
                "payload": {"user_id": user_id, "keywords": keywords, "weight": weight, "source": source,
                            "target_id": target_id, "find_matches": find_matches},
                "created_at": datetime.now(timezone.utc), "retries": 0, "status": "pending",
            })
            log.warning("Neo4j down, sở thích của %s đưa vào outbox: %s", user_id, e)
        except PyMongoError:
            log.warning("Không ghi được sở thích của %s (cả Neo4j lẫn outbox)", user_id)
    return keywords


def similar_users(user_id: str, limit: int = 10) -> list[dict]:
    """User có chung chủ đề quan tâm, chưa là bạn. Raise lỗi Neo4j để caller xử lý degraded."""
    with dbx.neo4j_driver.session() as s:
        rows = s.run(
            """MATCH (me:User {id: $id})-[a:INTERESTED_IN]->(k:Keyword)<-[b:INTERESTED_IN]-(o:User)
               WHERE o <> me AND NOT (me)-[:FRIEND]->(o)
               WITH me, o, k, a, b, COUNT { (k)<-[:INTERESTED_IN]-() } AS df
               WITH me, o, k, df, log(1.0 + CASE WHEN a.weight < b.weight THEN a.weight ELSE b.weight END)
                                  / log(1.0 + df) AS s
               ORDER BY s DESC
               WITH me, o, sum(s) AS score, collect({name: k.name, df: df})[..15] AS shared
               OPTIONAL MATCH (me)-[m:CONTENT_MATCH]-(o)
               RETURN o.id AS id, score, shared, m IS NOT NULL AS matched, m.topics AS match_topics
               // Trùng nội dung trực tiếp (xem/thích/bình luận/đăng bài khớp) luôn xếp trước
               ORDER BY matched DESC, coalesce(m.score, 0) DESC, score DESC LIMIT $limit""",
            id=user_id, limit=limit,
        ).data()
    top = max((r["score"] for r in rows), default=0) or 1
    # Chuẩn hóa về 0-5 để cộng được với số bạn chung (FoF) mà không lấn át
    return [{"user_id": r["id"], "interest_score": round(5 * r["score"] / top, 2), "content_match": r["matched"],
             "common_topics": display_topics(r["shared"], r["match_topics"] or [])}
            for r in rows]


def display_topics(shared: list[dict], prefer: list[str] = (), n: int = 3) -> list[str]:
    """Chọn chủ đề để hiển thị từ các từ khóa chung [{name, df}].

    Không có bộ tách từ tiếng Việt nên cụm 2 từ có thể ghép nhầm ('du lịch đà lạt' → 'lịch đà').
    Cụm ghép nhầm luôn có ít người dùng (df) hơn cụm thật, và chồng lấn với nhiều cụm hơn,
    nên ưu tiên: từ khóa của bài trùng khớp → cụm 2 từ → df cao → đứng trước trong câu → ít chồng lấn.
    ('cà phê sáng': 'cà phê' và 'phê sáng' luôn đi cùng nhau nên df bằng nhau → lấy cụm đứng trước.)
    """
    pos = {kw: i for i, kw in enumerate(prefer)}  # thứ tự xuất hiện trong bài (cụm 2 từ theo câu)
    bigrams = [k["name"].split() for k in shared if " " in k["name"]]
    overlaps = {k["name"]: sum(1 for b in bigrams if set(b) & set(k["name"].split())) for k in shared}
    ranked = sorted(shared, key=lambda k: (k["name"] not in pos, " " not in k["name"],
                                           -k["df"], pos.get(k["name"], 0), overlaps[k["name"]]))
    chosen, used = [], set()
    for k in ranked:
        words = set(k["name"].split())
        if words & used:
            continue
        chosen.append(k["name"])
        used |= words
        if len(chosen) == n:
            break
    return chosen


def rebuild_from_posts() -> dict:
    """Dựng lại sở thích của tác giả từ toàn bộ bài viết (idempotent: SET, không cộng dồn)."""
    ensure_schema()
    per_author: dict[str, Counter] = defaultdict(Counter)
    for p in dbx.db.posts.find({}, {"author_id": 1, "content": 1}):
        for kw in extract_keywords(p.get("content", "")):
            per_author[p["author_id"]][kw] += WEIGHT_POST
    rows = [{"user_id": uid, "kw": kw, "w": w} for uid, c in per_author.items() for kw, w in c.items()]
    with dbx.neo4j_driver.session() as s:
        for i in range(0, len(rows), 2000):
            s.run("""UNWIND $rows AS row
                     MATCH (u:User {id: row.user_id})
                     MERGE (k:Keyword {name: row.kw})
                     MERGE (u)-[r:INTERESTED_IN]->(k)
                     SET r.weight = row.w, r.updated_at = datetime()""", rows=rows[i:i + 2000])
        stats = s.run("MATCH (k:Keyword) RETURN count(k) AS keywords, "
                      "COUNT { ()-[:INTERESTED_IN]->() } AS edges").single().data()
    return {"authors": len(per_author), **stats}
