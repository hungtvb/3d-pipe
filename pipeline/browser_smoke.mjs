/** Proves hosted Chromium can create a WebGL2 context and render pixels.
 * Not Hồn Tranh game E2E. Use a separate gate for gameplay and real assets.
 */
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const out = path.resolve(process.argv[2] || 'artifacts/browser');
await fs.mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  args: ['--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage']
});
try {
  const page = await browser.newPage({ viewport: { width: 760, height: 540 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(process.env.SMOKE_URL || 'http://127.0.0.1:8118/browser-smoke.html', {waitUntil: 'load'});
  const result = await page.evaluate(() => {
    const canvas = document.querySelector('#webgl');
    const gl = canvas.getContext('webgl2', {antialias: false, preserveDrawingBuffer: true});
    if (!gl) return {ok: false, reason: 'No WebGL2 context'};
    const V = `#version 300 es
    in vec2 a; void main(){gl_Position=vec4(a,0.,1.);}`;
    const F = `#version 300 es
    precision highp float; out vec4 pixel;
    void main(){pixel=vec4(0.9,0.4,0.1,1.);}`;
    const compile = (type, source) => {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS))
        throw Error(gl.getShaderInfoLog(shader));
      return shader;
    };
    const program = gl.createProgram();
    gl.attachShader(program, compile(gl.VERTEX_SHADER, V));
    gl.attachShader(program, compile(gl.FRAGMENT_SHADER, F));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS))
      throw Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);
    const vertices = new Float32Array([0.,0.85,-0.85,-0.80,0.85,-0.80]);
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,vertices,gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(program,'a');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
    gl.viewport(0,0,canvas.width,canvas.height);
    gl.clearColor(0.03,0.07,0.13,1.);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawArrays(gl.TRIANGLES,0,3);
    gl.finish();
    const pixel = new Uint8Array(4);
    gl.readPixels(canvas.width >> 1,canvas.height >> 1,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);
    const success = pixel[0] > 170 && pixel[1] > 60 && pixel[2] < 80;
    document.querySelector('#status').textContent = success
       ? 'WebGL2 GPU smoke render: PASS' : 'WebGL2 GPU smoke render: FAIL';
    return {ok: success, sampledRGBA: Array.from(pixel), renderer: gl.getParameter(gl.RENDERER),
       width:canvas.width,height:canvas.height,glError:gl.getError()};
  });
  await page.screenshot({path:path.join(out,'webgl2.png')});
  const report = {...result, jsErrors: errors, verifiedScope: 'Generic browser WebGL2 only; not game E2E'};
  await fs.writeFile(path.join(out,'report.json'), JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
  if (!result.ok || errors.length || result.glError !== 0) process.exitCode = 1;
} finally {
  await browser.close();
}
