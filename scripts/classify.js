// scripts/classify.js - 输出到 m3u 子目录
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

(async () => {
    console.log('[分类脚本] 开始执行...');

    const inputFile = path.join(__dirname, '../m3u/all.m3u');
    if (!fs.existsSync(inputFile)) {
        console.error('[分类脚本] ❌ 错误：找不到 all.m3u 文件！路径：', inputFile);
        process.exit(1);
    }
    console.log(`[分类脚本] ✅ 找到 all.m3u：${inputFile}`);

    // 关键修改：输出目录改为 m3u 子目录
    const outputDir = path.join(__dirname, '../m3u');
    console.log(`[分类脚本] 输出目录：${outputDir}`);

    const categories = {
        'yangshi.m3u': ['cctv', '央视'],
        'weishi.m3u': ['卫视', '湖南卫视', '浙江卫视', '江苏卫视', '东方卫视', '北京卫视', '深圳卫视', '广东卫视', '天津卫视', '山东卫视', '安徽卫视', '辽宁卫视', '黑龙江卫视', '河北卫视', '河南卫视', '湖北卫视', '江西卫视', '广西卫视', '重庆卫视', '四川卫视', '贵州卫视', '云南卫视', '陕西卫视', '山西卫视', '内蒙古卫视', '新疆卫视', '西藏卫视', '青海卫视', '宁夏卫视', '甘肃卫视'],
        'difang.m3u': ['新闻综合', '生活频道', '影视', '都市', '公共', '教育', '少儿', '经济', '文体', '导视', '广播'],
        'gangtai.m3u': ['香港', '台湾', '港台', 'tvb', '翡翠', '明珠', '凤凰', '中天', '东森', '民视', '台视', '华视'],
        'guowai.m3u': ['cnn', 'bbc', 'nhk', 'kbs', 'abc', 'cbs', 'nbc', 'fox', 'sky', 'discovery', 'national geographic', 'hbo', 'espn', 'euronews', 'france', 'germany', 'russia', 'al jazeera', 'cgtn']
    };

    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    const streams = {};
    for (const cat of Object.keys(categories)) {
        const fullPath = path.join(outputDir, cat);
        streams[cat] = fs.createWriteStream(fullPath);
        streams[cat].write('#EXTM3U\n');
        console.log(`[分类脚本] 创建文件：${cat}`);
    }

    const content = fs.readFileSync(inputFile, 'utf-8');
    const lines = content.split(/\r?\n/);
    let currentInfo = null;
    let processedCount = 0, matchedCount = 0;

    for (let line of lines) {
        line = line.trim();
        if (line === '') continue;
        if (line.startsWith('#EXTINF')) {
            currentInfo = line;
        } else if (!line.startsWith('#') && currentInfo) {
            processedCount++;
            const combined = (currentInfo + ' ' + line).toLowerCase();
            let matched = false;
            for (const cat of Object.keys(categories)) {
                if (categories[cat].some(kw => combined.includes(kw.toLowerCase()))) {
                    streams[cat].write(currentInfo + '\n');
                    streams[cat].write(line + '\n');
                    matched = true;
                    matchedCount++;
                    break;
                }
            }
            currentInfo = null;
        }
    }

    const finishPromises = Object.values(streams).map(stream => {
        return new Promise((resolve) => {
            stream.on('finish', resolve);
            stream.end();
        });
    });
    await Promise.all(finishPromises);

    console.log(`[分类脚本] 处理完成！总频道数：${processedCount}，匹配分类数：${matchedCount}`);
    for (const cat of Object.keys(categories)) {
        const filePath = path.join(outputDir, cat);
        try {
            const stat = fs.statSync(filePath);
            console.log(`   ${cat} (${stat.size} bytes)`);
        } catch (err) {
            console.log(`   ${cat} (文件不存在: ${err.message})`);
        }
    }
    console.log('[分类脚本] 脚本正常结束');
})();
