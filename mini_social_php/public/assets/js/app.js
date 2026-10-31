document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('textarea[maxlength]').forEach(el=>{const hint=document.createElement('small');hint.className='char-counter';hint.textContent=`${el.value.length}/${el.maxLength}`;el.insertAdjacentElement('afterend',hint);el.addEventListener('input',()=>hint.textContent=`${el.value.length}/${el.maxLength}`);});
  document.querySelectorAll('form').forEach(form=>form.addEventListener('submit',()=>{const button=form.querySelector('button[type="submit"],button:not([type])');if(button && !button.dataset.noLoading){button.disabled=true;button.dataset.originalText=button.textContent;button.textContent='Đang xử lý...';}}));
});
