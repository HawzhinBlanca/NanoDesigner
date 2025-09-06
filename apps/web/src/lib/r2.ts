export async function putWithRetry(url: string, file: File, maxAttempts = 3) {
  let attempt = 0;
  let delay = 250;
  // Note: backend provides signed URL via separate service; placeholder expects direct PUT URL
  while (attempt < maxAttempts) {
    const res = await fetch(url, { method: "PUT", body: file });
    if (res.ok) return true;
    await new Promise((r) => setTimeout(r, (delay += Math.random() * 150)));
    attempt++;
  }
  throw new Error("Upload failed");
}

