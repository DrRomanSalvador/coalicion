#!/usr/bin/env node
import { pipeline, env } from "@huggingface/transformers";
import http from "node:http";

env.cacheDir = process.env.TRANSFORMERS_CACHE || "./.cache";
env.useFSCache = true;
env.useWasmCache = true;

const MODEL = "onnx-community/Qwen3-0.6B-ONNX";
const DTYPE = "q4f16";
const DEVICE = process.env.COLMENA_AI_DEVICE || "cpu";
const PORT = Number(process.env.COLMENA_AI_PORT || "8765");

function responseContent(result) {
  const generated = Array.isArray(result) ? result[0]?.generated_text : undefined;
  if (typeof generated === "string") return generated.trim();
  if (Array.isArray(generated)) {
    const last = generated.at(-1);
    if (last && typeof last.content === "string") return last.content.trim();
    return generated.map(x => typeof x?.content === "string" ? x.content : "").join("").trim();
  }
  return "";
}

function promptFor(job) {
  return [
    "<|im_start|>system",
    "You are an isolated COALICION worker agent. Return a concise independent assessment. Do not govern or modify the repository.",
    "<|im_end|>",
    "<|im_start|>user",
    JSON.stringify(job),
    "<|im_end|>",
    "<|im_start|>assistant"
  ].join("\n");
}

async function infer(pipe, job) {
  const result = await pipe(promptFor(job), {
    max_new_tokens: 96,
    do_sample: false,
    return_full_text: false,
  });
  const content = responseContent(result);
  if (!content) throw new Error("empty generated content");
  return { model: MODEL, dtype: DTYPE, device: DEVICE, content };
}

async function main() {
  const pipe = await pipeline("text-generation", MODEL, { dtype: DTYPE, device: DEVICE });

  if (process.argv.includes("--warm")) {
    console.log(JSON.stringify({ warm: true, model: MODEL, dtype: DTYPE, device: DEVICE }));
    return;
  }

  if (process.argv.includes("--server")) {
    const server = http.createServer(async (req, res) => {
      if (req.method === "GET" && req.url === "/health") {
        res.writeHead(200, {"content-type":"application/json"});
        res.end(JSON.stringify({status:"PASS",model:MODEL,device:DEVICE}));
        return;
      }
      if (req.method !== "POST" || req.url !== "/infer") {
        res.writeHead(404); res.end(); return;
      }
      try {
        let body = "";
        for await (const chunk of req) body += chunk;
        const data = await infer(pipe, JSON.parse(body));
        res.writeHead(200, {"content-type":"application/json"});
        res.end(JSON.stringify(data));
      } catch (err) {
        res.writeHead(500, {"content-type":"application/json"});
        res.end(JSON.stringify({error:String(err?.stack || err)}));
      }
    });
    server.listen(PORT, "127.0.0.1", () =>
      console.log(JSON.stringify({server:"PASS",model:MODEL,device:DEVICE,port:PORT}))
    );
    return;
  }

  const input = await new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", chunk => data += chunk);
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
  process.stdout.write(JSON.stringify(await infer(pipe, JSON.parse(input))) + "\n");
}

main().catch(err => {
  console.error(err?.stack || String(err));
  process.exit(1);
});
