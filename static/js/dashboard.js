(() => {
  const canvas=document.getElementById('sales-chart'); if(!canvas || !window.Chart)return;
  const ctx=canvas.getContext('2d');
  const gradient=ctx.createLinearGradient(0,0,0,220);gradient.addColorStop(0,'#a7bd7045');gradient.addColorStop(1,'#a7bd7000');
  new Chart(canvas,{type:'line',data:{labels:JSON.parse(document.getElementById('chart-labels').textContent),datasets:[{data:JSON.parse(document.getElementById('chart-values').textContent).map(Number),borderColor:'#8ba568',backgroundColor:gradient,borderWidth:2,fill:true,tension:.4,pointRadius:3,pointBackgroundColor:'#fff',pointBorderColor:'#8ba568',pointBorderWidth:2}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{displayColors:false,backgroundColor:'#28533d',padding:12}},scales:{x:{grid:{display:false},border:{display:false},ticks:{color:'#a9b69a',font:{size:8},maxTicksLimit:8}},y:{beginAtZero:true,border:{display:false},grid:{color:'#edf2e5',drawTicks:false},ticks:{color:'#afba9f',font:{size:8},padding:10,maxTicksLimit:5}}}}});
})();
