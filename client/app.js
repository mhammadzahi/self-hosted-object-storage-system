import fs from "fs";
import path from "path";
import FormData from "form-data";

const BASE_URL = "http://127.0.0.1:8001";

// Upload file
export async function uploadFile(filePath, folder = "") {
  const form = new FormData();
  form.append("file", fs.createReadStream(filePath));

  const url = `${BASE_URL}/upload/${folder ? `?folder=${folder}` : ""}`;

  const res = await fetch(url, {
    method: "POST",
    body: form,
    headers: form.getHeaders(),
  });

  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  const data = await res.json();
  console.log("✅ Uploaded:", data);
  return data;
}




// Download file
export async function downloadFile(fileId, outputPath, folder = "") {
  const url = `${BASE_URL}/download/${fileId}${folder ? `?folder=${folder}` : ""}`;
  const res = await fetch(url);

  if (!res.ok) throw new Error(`Download failed: ${res.statusText}`);

  const fileStream = fs.createWriteStream(outputPath);
  await new Promise((resolve, reject) => {
    res.body.pipe(fileStream);
    res.body.on("error", reject);
    fileStream.on("finish", resolve);
  });

  console.log(`Downloaded to: ${outputPath}`);
}

// Example usage
const main = async () => {
  try {
    const uploaded = await uploadFile("test.png", "images");
    console.log("Uploaded File ID:", uploaded.file_id);
    // await downloadFile(uploaded.file_id, path.resolve(`downloaded_${uploaded.file_id}.png`), "images");
  }
  catch (err) {
    console.error("Error:", err.message);
  }
};

main();
