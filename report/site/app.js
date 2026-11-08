'use strict';
const board=document.getElementById('board'),ctx=board.getContext('2d'),status=document.getElementById('status'),layout=document.getElementById('layout');
let report,images=new Map();
function text(size,top,left,color,value){ctx.fillStyle=color===255?'white':'black';ctx.font=`700 ${size}px system-ui,"Noto Sans CJK SC",sans-serif`;ctx.textBaseline='top';ctx.fillText(value,left,top+Math.floor(size*.45));}
async function refresh(){try{
 const response=await fetch('report.json?v='+Date.now(),{cache:'no-store'});if(!response.ok)throw Error('HTTP '+response.status);
 const next=await response.json();if(next.schema_version!==1||!Array.isArray(next.commands))throw Error('报告格式不兼容');
 const paths=[...new Set([...next.commands,...(next.portrait_commands||[])].filter(s=>s.startsWith('I|')).map(s=>s.split('|').slice(5).join('|')))];
 await Promise.all(paths.map(path=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>{images.set(path,im);resolve();};im.onerror=reject;im.src='assets/'+path.split('/').pop();})));
 report=next;draw();status.textContent='报告生成于 '+report.generated_at+' · '+(report.errors.join('；')||'缺少数据的项目显示未配置');
 }catch(e){status.textContent='读取失败，保留已有画面：'+e.message;}}
function draw(){if(!report)return;const portrait=layout.value==='portrait',spec=report.layouts[layout.value];board.width=spec.width;board.height=spec.height;ctx.fillStyle='white';ctx.fillRect(0,0,board.width,board.height);
 for(const line of (portrait?report.portrait_commands:report.commands)){const a=line.split('|');if(a[0]==='T')text(+a[1],+a[2],+a[3],+a[4],a.slice(5).join('|'));
 else if(a[0]==='I'){const im=images.get(a.slice(5).join('|'));if(im)ctx.drawImage(im,+a[1],+a[2],+a[3]||im.width,+a[4]||im.height);}
 else if(a[0]==='R'){ctx.fillStyle=`rgb(${a[5]},${a[5]},${a[5]})`;ctx.fillRect(+a[1],+a[2],+a[3],+a[4]);}}
 const c=spec,b={size:spec.battery_size,top:spec.battery_top,left:spec.battery_left,x:spec.battery_x,y:spec.battery_y,w:spec.battery_w,h:spec.battery_h};
 const now=new Date(),aligned=new Date(Math.floor(now.getTime()/600000)*600000);
 text(c.size,c.top,c.left,0,new Intl.DateTimeFormat('en-GB',{timeZone:report.timezone,hour:'2-digit',minute:'2-digit',hour12:false}).format(aligned));
 text(b.size,b.top,b.left,0,'电量 --%');ctx.strokeStyle='black';ctx.lineWidth=3;ctx.strokeRect(b.x,b.y,b.w,b.h);}
layout.addEventListener('change',draw);
refresh();setInterval(draw,60000);setInterval(refresh,600000);
