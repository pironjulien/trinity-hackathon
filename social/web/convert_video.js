import ffmpeg from 'ffmpeg-static';
import { exec } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Correct path resolution considering we run from 'social/web'
const src = path.resolve('public/videos/author.mp4');
const dest = path.resolve('public/videos/author.webm');

console.log(`Using ffmpeg at: ${ffmpeg}`);
console.log(`Converting: ${src}`);
console.log(`To: ${dest}`);

// -an (remove audio) since it's a background video and we want to save space/bandwidth
// -y to overwrite
const cmd = `"${ffmpeg}" -y -i "${src}" -c:v libvpx-vp9 -b:v 2M -an "${dest}"`;

exec(cmd, (error, stdout, stderr) => {
    if (error) {
        console.error(`Error: ${error.message}`);
        return;
    }
    console.log('Conversion complete!');
});
