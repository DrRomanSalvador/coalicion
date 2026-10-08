#!/usr/bin/env node
import { pipeline, env } from "@huggingface/transformers";

env.cacheDir = process.env.TRANSFORMERS_CACHE || "./.cache";
env.useFSCache = true;
env.useWasmCache = true;

const MODEL = "onnx-community/SmolLM2-135M-Instruct-ONNX-MHA";
const DTYPE = "q4f16";

async function main() {
  const pipe = await pipeline("text-generation", MODEL, { dtype: DTYPE, device: "wasm" });

  if (process.argv.includes("--warm")) {
    console.log(JSON.stringify({warm:true, model:MODEL, dtype:DTYPE}));
    return;
  }

  const input = await new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", chunk => data += chunk);
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
  const job = JSON.parse(input);
  const prompt = [
    "<|im_start|>system",
    "You are an isolated COALICION worker agent. Return a concise JSON object describing your independent assessment. Do not govern or modify the repository.",
    "<|im_end|>",
    "<|im_start|>user",
    JSON.stringify(job),
    "<|im_end|>",
    "<|im_start|>assistant"
  ].join("\n");

  const result = await pipe(prompt, { max_new_tokens: 96, do_sample: false, return_full_text: false });
  const generated = Array.isArray(result) ? result[0]?.generated_text : "";
  const content = typeof generated === "string" ? generated.trim() : "";
  if (!content) throw new Error("empty generated content");
  process.stdout.write(JSON.stringify({model:MODEL, dtype:DTYPE, content}) + "\n");
}

main().catch(err => {
  console.error(err?.stack || String(err));
  process.exit(1);
});
