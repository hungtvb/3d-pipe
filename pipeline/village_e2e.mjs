/** Real manifest → GLB → browser E2E with reproducible screenshot artifacts. */
import { chromium } from "playwright";
import { mkdir, writeFile, stat } from "node:fs/promises";
const dir="artifacts/village-browser";
await mkdir(dir,{recursive:true});
const browser=await chromium.launch({headless:true,args:[
  "--enable-webgl","--use-gl=angle","--use-angle=swiftshader",
  "--enable-unsafe-swiftshader","--disable-dev-shm-usage"
]});
let failed=false;
try{
  const page=await browser.newPage({viewport:{width:1100,height:700},deviceScaleFactor:1});
  const errors=[];page.on("pageerror",e=>errors.push(String(e)));
  page.on("console",msg=>{if(msg.type()==="error")errors.push(msg.text());});
  const response=await page.goto("http://127.0.0.1:8118/examples/village-blockout/",{waitUntil:"load"});
  if(!response?.ok())throw Error("Preview HTML returned "+response?.status());
  await page.waitForFunction(()=>window.__sceneReady===true||!!window.__sceneError,{timeout:20000});
  const first=await page.evaluate(()=>{
    if(window.__sceneError)throw Error(window.__sceneError);
    const {yaw}=window.__sceneCamera;
    const c=document.querySelector("canvas");
    const gl=c.getContext("webgl2");
    const w=c.width,h=c.height,px=new Uint8Array(4), samples=[];
    // Pixel readback confirms we actually drew GLB geometry, not just a canvas.
    for(let y=1;y<=7;y++)for(let x=1;x<=11;x++){
      gl.readPixels(Math.floor(w*x/12),Math.floor(h*y/8),1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);
      samples.push([...px]);
    }
    const scenePixels=samples.filter(p=>Math.abs(p[0]-10)>8||Math.abs(p[1]-19)>8||Math.abs(p[2]-33)>8).length;
    return {...window.__sceneMetrics,scenePixels,totalSamples:samples.length,yaw};
  });
  await page.screenshot({path:dir+"/initial.png",fullPage:true});
  await page.keyboard.press("ArrowRight");
  const second=await page.evaluate(()=>({yaw:window.__sceneCamera.yaw,metrics:window.__sceneMetrics}));
  await page.screenshot({path:dir+"/rotated.png",fullPage:true});
  if(first.triangles<900||first.drawCalls<4||first.scenePixels<4||first.glError!==0)throw Error("Geometry/render gate failed: "+JSON.stringify(first));
  if(second.yaw<=first.yaw+0.05||second.metrics.glError!==0)throw Error("Interactive camera gate failed");
  if(errors.length)throw Error("Browser errors: "+errors.join("; "));
  const report={ok:true,scope:"Actual manifest-generated village GLB + camera E2E (not Hồn Tranh gameplay)",
     first,rotatedYaw:second.yaw,errors,viewport:[1100,700],renderer:"Chromium SwiftShader"};
  await writeFile(dir+"/report.json",JSON.stringify(report,null,2));
  console.log("VILLAGE_BROWSER_E2E_PASS",JSON.stringify(report));
  for(const img of ["initial.png","rotated.png"])if((await stat(dir+"/"+img)).size<5000)throw Error("Screenshot too small: "+img);
}catch(e){
  failed=true;console.error("VILLAGE_BROWSER_E2E_FAIL",e);
  await writeFile(dir+"/failure.txt",String(e));
}finally{await browser.close();}
if(failed)process.exitCode=1;
