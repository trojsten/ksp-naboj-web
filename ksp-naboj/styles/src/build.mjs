import * as esbuild from "esbuild"
import {stimulusPlugin} from "esbuild-plugin-stimulus"

let appOptions = {
  plugins: [stimulusPlugin()],
  entryPoints: ["ksp-naboj/styles/src/app.js"],
  bundle: true,
  minify: true,
  outdir: "ksp-naboj/styles/static",
  entryNames: "bundle",
  loader: {
    ".ttf": "dataurl",
  },
}

let workerOptions = {
  entryPoints: ["monaco-editor/esm/vs/editor/editor.worker.js"],
  bundle: true,
  minify: true,
  outfile: "ksp-naboj/styles/static/editor.worker.js",
}

if (process.argv.indexOf("watch") !== -1) {
  let appCtx = await esbuild.context(appOptions)
  let workerCtx = await esbuild.context(workerOptions)
  await Promise.all([appCtx.watch(), workerCtx.watch()])
} else {
  await Promise.all([esbuild.build(appOptions), esbuild.build(workerOptions)])
}
