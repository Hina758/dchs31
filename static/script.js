// static/script.js
(function(){
  const form = document.getElementById('form');
  const studentNo = document.getElementById('studentNo');
  const nameI = document.getElementById('name');
  const crush = document.getElementById('crush');
  const submitBtn = document.getElementById('submitBtn');

  if (submitBtn && studentNo && nameI && crush){
    function checkInputs(){ submitBtn.disabled = !(studentNo.value.trim() && nameI.value.trim() && crush.value.trim()); }
    [studentNo,nameI,crush].forEach(i=>i.addEventListener('input', checkInputs));
    if (form) form.addEventListener('keydown', e=>{ if (e.key === 'Enter') e.preventDefault(); });

    submitBtn.addEventListener('click', async ()=>{
      const s = studentNo.value.trim(), n = nameI.value.trim(), c = crush.value.trim();

      // 관리자 바로가기 로직이 완전히 삭제됨

      submitBtn.disabled = true;
      submitBtn.innerText = '제출 중...';
      try {
        const res = await fetch('/submit', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ studentNo: s, name: n, crush: c })
        });
        if (res.status === 409) { alert('이미 제출된 학번/이름입니다! 어디서!'); submitBtn.disabled=false; submitBtn.innerText='시작!'; return; }
        if (!res.ok) { alert('서버 오류'); submitBtn.disabled=false; submitBtn.innerText='시작!'; return; }
        localStorage.setItem('lm_payload', JSON.stringify({ studentNo: s, name: n, crush: c }));
        location.href = '/result-wait';
      } catch(e) {
        alert('네트워크 오류');
        submitBtn.disabled=false;
        submitBtn.innerText='시작!';
      }
    });
  }
})();