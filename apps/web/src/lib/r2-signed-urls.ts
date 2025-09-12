import { api } from "./api";

export interface R2SignedUrlResponse {
  uploadUrl: string;
  downloadUrl: string;
  key: string;
  expiresAt: Date;
}

export async function getSignedUploadUrl(
  projectId: string,
  fileName: string,
  fileType: string
): Promise<R2SignedUrlResponse> {
  // Call the backend API to get a signed URL from R2
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/r2/signed-url`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("auth_token")}`,
      },
      body: JSON.stringify({
        projectId,
        fileName,
        fileType,
        operation: "upload",
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to get signed URL: ${response.statusText}`);
  }

  return response.json();
}

export async function uploadToR2(
  signedUrl: string,
  file: File,
  onProgress?: (progress: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && onProgress) {
        const percentComplete = (event.loaded / event.total) * 100;
        onProgress(Math.round(percentComplete));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new Error(`Upload failed with status ${xhr.status}`));
      }
    });

    xhr.addEventListener("error", () => {
      reject(new Error("Upload failed"));
    });

    xhr.open("PUT", signedUrl);
    xhr.setRequestHeader("Content-Type", file.type);
    xhr.send(file);
  });
}