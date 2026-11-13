document.addEventListener('DOMContentLoaded', () => {
  // Ẩn ô bình luận, bấm "Bình luận" để mở/đóng
  document.querySelectorAll('.comment-form:not(.is-open)').forEach(form => { form.style.display = 'none'; });
  document.querySelectorAll('.comment-toggle').forEach(button => button.addEventListener('click', () => {
    const form = button.closest('.post-card')?.querySelector('.comment-form');
    if (!form) return;
    const open = form.style.display !== 'flex';
    form.style.display = open ? 'flex' : 'none';
    if (open) form.querySelector('input[name=content]')?.focus();
  }));
  // Ô tìm kiếm trên thanh đầu trang → tìm bài viết (GET /posts/search)
  const search = document.getElementById('globalSearch');
  if (search) search.addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const q = search.value.trim();
    if (q) window.location.href = 'feed.php?q=' + encodeURIComponent(q);
  });
});
