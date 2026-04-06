import "dotenv/config";
import fs from "fs";
import path from "path";
import { Storage } from "@google-cloud/storage";
import type { Manuscript } from "../src/NarrationVideo/types";

const BUCKET_NAME = process.env.GCS_BUCKET_NAME;
if (!BUCKET_NAME) {
  throw new Error("GCS_BUCKET_NAME is not set in .env");
}

async function uploadToGCS(
  videoPath: string,
  manuscriptPath?: string,
): Promise<string> {
  const credPath = path.resolve("credentials/service-account.json");
  if (!fs.existsSync(credPath)) {
    throw new Error(`Service account key not found at ${credPath}`);
  }

  const storage = new Storage({ keyFilename: credPath });
  const bucket = storage.bucket(BUCKET_NAME as string);

  let fileName = `video_${Date.now()}.mp4`;
  if (manuscriptPath && fs.existsSync(manuscriptPath)) {
    const manuscript: Manuscript = JSON.parse(
      fs.readFileSync(manuscriptPath, "utf-8"),
    );
    fileName = `${manuscript.title}_${Date.now()}.mp4`;
  }

  console.log(`Uploading ${videoPath} → gs://${BUCKET_NAME}/${fileName}`);

  await bucket.upload(videoPath, {
    destination: fileName,
    metadata: { contentType: "video/mp4" },
  });

  const publicUrl = `https://storage.googleapis.com/${BUCKET_NAME}/${encodeURIComponent(fileName)}`;
  console.log(`Uploaded: gs://${BUCKET_NAME}/${fileName}`);
  console.log(`  URL: ${publicUrl}`);

  // Save URL to file for pipeline integration
  const urlOutputPath = path.resolve("out/video_url.txt");
  fs.writeFileSync(urlOutputPath, publicUrl, "utf-8");
  console.log(`  URL saved to: ${urlOutputPath}`);

  return publicUrl;
}

// CLI entry
const videoPath = process.argv[2] || "out/video.mp4";
const manuscriptPath = process.argv[3] || "input/manuscript.json";

if (!fs.existsSync(videoPath)) {
  console.error(`Video file not found: ${videoPath}`);
  process.exit(1);
}

uploadToGCS(videoPath, manuscriptPath).catch((err) => {
  console.error("Failed:", err);
  process.exit(1);
});
