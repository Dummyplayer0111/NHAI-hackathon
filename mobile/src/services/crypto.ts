import { hmac } from "@noble/hashes/hmac";
import { sha256 } from "@noble/hashes/sha256";
import { utf8ToBytes } from "@noble/hashes/utils";

function base64Url(bytes: Uint8Array): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  let output = "";
  for (let index = 0; index < bytes.length; index += 3) {
    const first = bytes[index];
    const second = bytes[index + 1];
    const third = bytes[index + 2];
    const triplet = (first << 16) | ((second ?? 0) << 8) | (third ?? 0);
    output += alphabet[(triplet >> 18) & 63];
    output += alphabet[(triplet >> 12) & 63];
    output += index + 1 < bytes.length ? alphabet[(triplet >> 6) & 63] : "=";
    output += index + 2 < bytes.length ? alphabet[triplet & 63] : "=";
  }
  return output.replace(/\+/g, "-").replace(/\//g, "_");
}

export function canonicalJson(payload: Record<string, unknown>): string {
  const sorted: Record<string, unknown> = {};
  Object.keys(payload)
    .sort()
    .forEach((key) => {
      sorted[key] = payload[key];
    });
  return JSON.stringify(sorted);
}

export function signPayload(payload: Record<string, unknown>, secret: string): string {
  const digest = hmac(sha256, utf8ToBytes(secret), utf8ToBytes(canonicalJson(payload)));
  return base64Url(digest);
}
