// Offline-capable WebGL2 GLB viewer. Assumes float32 vec3 positions/normals,
// indexed triangle primitives, identity nodes (this pipeline's blockout contract).
const canvas=document.querySelector("#scene"), status=document.querySelector("#status");
const gl=canvas.getContext("webgl2",{preserveDrawingBuffer:true,antialias:true});
if(!gl)throw Error("WebGL2 unavailable");
window.__sceneReady=false;
const vertexSource = "#version 300 es\nin vec3 position; in vec3 normal; uniform mat4 vp; out vec3 N;out vec3 P;\nvoid main(){N=normal;P=position;gl_Position=vp*vec4(position,1.);}";
const fragmentSource = "#version 300 es\nprecision highp float;in vec3 N;in vec3 P;uniform vec4 color;uniform vec3 eye;out vec4 pixel;\nvoid main(){float a=max(dot(normalize(N),normalize(vec3(-.5,.8,.6))),0.);vec3 c=color.rgb*(.46+.54*a);float fog=smoothstep(40.,110.,length(P-eye));pixel=vec4(mix(c,vec3(.10,.14,.18),fog*.53),1.);}";
function compile(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
const program=gl.createProgram();gl.attachShader(program,compile(gl.VERTEX_SHADER,vertexSource));gl.attachShader(program,compile(gl.FRAGMENT_SHADER,fragmentSource));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);
const attr={p:gl.getAttribLocation(program,"position"),n:gl.getAttribLocation(program,"normal")},uniform={vp:gl.getUniformLocation(program,"vp"),color:gl.getUniformLocation(program,"color"),eye:gl.getUniformLocation(program,"eye")};
const sub=(a,b)=>a.map((v,i)=>v-b[i]),cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0),norm=a=>a.map(v=>v/Math.hypot(...a));
function lookAt(eye,target){const z=norm(sub(eye,target)),x=norm(cross([0,1,0],z)),y=cross(z,x);return [x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1];}
function perspective(aspect){const f=1/Math.tan(Math.PI/7.6),n=1/(.1-250);return [f/aspect,0,0,0,0,f,0,0,0,0,(250+.1)*n,-1,0,0,2*250*.1*n,0];}
function mul(a,b){const o=new Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++){let sum=0;for(let k=0;k<4;k++)sum+=a[k*4+r]*b[c*4+k];o[c*4+r]=sum;}return o;}
const camera={yaw:.63,pitch:.52,dist:69};window.__sceneCamera=camera;
const state={primitives:[],triangles:0,bytes:0};
function render(){
const w=Math.max(1,Math.floor(canvas.clientWidth*Math.min(devicePixelRatio,1.5))),h=Math.max(1,Math.floor(canvas.clientHeight*Math.min(devicePixelRatio,1.5)));canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);
gl.clearColor(.04,.075,.13,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);
const {yaw,pitch,dist}=camera,eye=[dist*Math.sin(yaw)*Math.cos(pitch),2+dist*Math.sin(pitch),dist*Math.cos(yaw)*Math.cos(pitch)],target=[0,2,0];
gl.useProgram(program);gl.uniformMatrix4fv(uniform.vp,false,new Float32Array(mul(perspective(w/h),lookAt(eye,target))));gl.uniform3fv(uniform.eye,new Float32Array(eye));
for(const p of state.primitives){gl.uniform4fv(uniform.color,new Float32Array(p.color));gl.bindVertexArray(p.vao);gl.drawElements(gl.TRIANGLES,p.count,gl.UNSIGNED_INT,0);}
gl.bindVertexArray(null);window.__sceneMetrics={triangles:state.triangles,drawCalls:state.primitives.length,bytes:state.bytes,eye,glError:gl.getError(),width:w,height:h};
}
async function load(){
const response=await fetch("../../artifacts/village-blockout.glb");if(!response.ok)throw Error("GLB HTTP "+response.status);
const buffer=await response.arrayBuffer(),view=new DataView(buffer);
if(view.getUint32(0,true)!==0x46546c67||view.getUint32(4,true)!==2||view.getUint32(8,true)!==buffer.byteLength)throw Error("Invalid GLB");
const len=view.getUint32(12,true),json=JSON.parse(new TextDecoder().decode(new Uint8Array(buffer,20,len))),start=28+len;
if(view.getUint32(16,true)!==0x4e4f534a||view.getUint32(24+len,true)!==0x004e4942)throw Error("Missing GLB chunks");
const binLength=view.getUint32(20+len,true),accessor=(i)=>{
const a=json.accessors[i],v=json.bufferViews[a.bufferView],offset=start+(v.byteOffset||0)+(a.byteOffset||0),size=a.type==="VEC3"?3:1;
const bytes=a.componentType===5123?2:4,count=a.count*size,reader=new DataView(buffer,offset,count*bytes);
if(offset+count*bytes>start+binLength)throw Error("Bad accessor bounds");
const result=a.componentType===5126?new Float32Array(count):new Uint32Array(count);
for(let n=0;n<count;n++)result[n]=a.componentType===5126?reader.getFloat32(n*4,true):a.componentType===5125?reader.getUint32(n*4,true):reader.getUint16(n*2,true);
return result;};
for(const m of json.meshes)for(const p of m.primitives){
const pos=accessor(p.attributes.POSITION),normal=accessor(p.attributes.NORMAL),indices=accessor(p.indices),vao=gl.createVertexArray();gl.bindVertexArray(vao);
function bind(data,location){const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW);gl.enableVertexAttribArray(location);gl.vertexAttribPointer(location,3,gl.FLOAT,false,0,0);}
bind(pos,attr.p);bind(normal,attr.n);const ib=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint32Array(indices),gl.STATIC_DRAW);gl.bindVertexArray(null);
const color=json.materials[p.material]?.pbrMetallicRoughness?.baseColorFactor||[.7,.7,.7,1];
state.primitives.push({vao,count:indices.length,color});state.triangles+=indices.length/3;
}
state.bytes=buffer.byteLength;render();status.textContent="RENDERED · "+state.triangles+" TRIS · "+state.primitives.length+" DRAWS";window.__sceneReady=true;
}
let active=false,lastX=0,lastY=0;canvas.addEventListener("pointerdown",e=>{active=true;lastX=e.clientX;lastY=e.clientY;canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener("pointerup",()=>active=false);
canvas.addEventListener("pointermove",e=>{if(!active)return;camera.yaw+=(e.clientX-lastX)*.005;camera.pitch=Math.max(.06,Math.min(1.45,camera.pitch-(e.clientY-lastY)*.005));lastX=e.clientX;lastY=e.clientY;if(window.__sceneReady)render();});
canvas.addEventListener("wheel",e=>{e.preventDefault();camera.dist=Math.max(18,Math.min(120,camera.dist*(e.deltaY>0?1.12:.89)));if(window.__sceneReady)render();},{passive:false});
window.addEventListener("keydown",e=>{if(e.key==="ArrowRight")camera.yaw+=.15;else if(e.key==="ArrowLeft")camera.yaw-=.15;else if(e.key==="ArrowUp")camera.pitch=Math.min(1.45,camera.pitch+.08);else if(e.key==="ArrowDown")camera.pitch=Math.max(.06,camera.pitch-.08);else return;e.preventDefault();if(window.__sceneReady)render();});
window.addEventListener("resize",()=>{if(window.__sceneReady)render();});
load().catch(e=>{window.__sceneError=String(e);status.textContent="FAILED · "+e.message;console.error(e);});
