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

      // MODIFIED: admin shortcuts, 이 부분을 수정했습니다!
      if (s === '01911' && n === '이재율' && c === '박준혁') { location.href = '/admin'; return; }
      if (s === '77777' && n === '허찬영' && c === '한승원') { location.href = '/admin2'; return; }

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
        // save minimal local for result checking flow; now go to wait page
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