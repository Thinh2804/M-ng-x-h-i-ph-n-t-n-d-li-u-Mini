<?php
// Central configuration. Keep all API routes here so they match backend-python/app/routers.
// {user_id}/{post_id} are replaced by apiPath(); user_id is the logged-in user unless given.
return [
    'app_name' => 'UniConnect',
    // Đổi sang IP LAN của PC4 khi PHP và FastAPI chạy khác máy (hoặc đặt biến môi trường API_BASE_URL)
    'base_url' => getenv('API_BASE_URL') ?: 'http://127.0.0.1:8000',
    'api_prefix' => '',
    'timeout' => 20, // bầu lại primary mất ~15s; ngắn hơn sẽ báo lỗi nhầm dù đã ghi
    'endpoints' => [
        'register' => '/users',                          // POST {username, password, full_name}
        'login' => '/users/login',                       // POST {username, password} → user (_id, role...)
        'users' => '/users?limit=1000',                  // GET danh sách user (tra tên bạn bè)
        'profile' => '/users/{user_id}',                 // GET hồ sơ
        'user_posts' => '/posts/by-author/{user_id}',    // GET bài viết của user (targeted - 1 shard)
        'feed' => '/social/feed/{user_id}',              // GET {degraded, friend_count, posts}
        'posts' => '/posts',                             // POST {author_id, content, image_urls}
        'post' => '/posts/{post_id}',                    // GET 1 bài viết
        'post_view' => '/posts/{post_id}/view',          // POST ghi nhận đã xem (sở thích theo chủ đề)
        'like' => '/posts/{post_id}/like',               // POST
        'post_comments' => '/posts/{post_id}/comments',  // GET bình luận của bài
        'comments' => '/posts/comments',                 // POST {post_id, author_id, content}
        'friends' => '/social/friends/{user_id}',        // GET {friends: [user_id...]}
        'friend_add' => '/social/friends',               // POST {from_user, to_user}
        'suggestions' => '/social/suggestions/{user_id}',// GET {degraded, suggestions}
        'search' => '/posts/search?q={q}',               // GET tìm bài (scatter-gather)
        'health' => '/admin/health',                     // GET {mongo_cluster, neo4j, shards, outbox_pending}
        'shards' => '/admin/shard-distribution',         // GET số document mỗi shard
        'outbox_process' => '/admin/outbox/process',     // POST xử lý outbox ngay
    ],
];
