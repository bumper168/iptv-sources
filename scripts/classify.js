// scripts/classify.js
const fs = require('fs');
const path = require('path');

// 输入文件：项目构建后生成的 all.m3u 的路径（相对于项目根目录）
const inputFile = path.join(__dirname, '../m3u/all.m3u');
const outputDir = path.join(__dirname, '../m3u');

// 分类规则（关键词匹配，不区分大小写，因为后面会统一小写比较）
const categories = {
    '央视.m3u': ['cctv', '央视'],
    '卫视.m3u': ['卫视', '湖南卫视', '浙江卫视', '江苏卫视', '东方卫视', '北京卫视', '深圳卫视', '广东卫视', '天津卫视', '山东卫视', '安徽卫视', '辽宁卫视', '黑龙江卫视', '河北卫视', '河南卫视', '湖北卫视', '江西卫视', '广西卫视', '重庆卫视', '四川卫视', '贵州卫视', '云南卫视', '陕西卫视', '山西卫视', '内蒙古卫视', '新疆卫视', '西藏卫视', '青海卫视', '宁夏卫视', '甘肃卫视'],
    '地方.m3u': ['新闻综合', '生活频道', '影视', '都市', '公共', '教育', '少儿', '经济', '文体', '导视', '广播'],
    '港台.m3u': ['香港', '台湾', '港台', 'tvb', '翡翠', '明珠', '凤凰', '中天', '东森', '民视', '台视', '华视'],
    '国外.m3u': ['cnn', 'bbc', 'nhk', 'kbs', 'abc', 'cbs', 'nbc', 'fox', 'sky', 'discovery', 'national geographic', 'hbo', 'espn', 'euronews', 'france', 'germany', 'russia', 'al jazeera', 'cgtn']
};

// 初始化输出流
const streams = {};
for (let cat in categories) {
    const fullPath = path.join(outputDir, cat);
    streams[cat] = fs.createWriteStream(fullPath);
    streams[cat].write('#EXTM3U\n'); // M3U 文件头部
}

// 读取 all.m3u 文件
if (!fs.existsSync(inputFile)) {
    console.error('错误：找不到 all.m3u 文件，请确保先运行构建命令');
    process.exit(1);
}

const content = fs.readFileSync(inputFile, 'utf-8');
const lines = content.split(/\r?\n/);

let currentEntry = null; // 存储当前频道的完整两行（信息行+URL行）

for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line === '') continue;

    // 以 #EXTINF 开头的行是频道信息行
    if (line.startsWith('#EXTINF')) {
        currentEntry = { info: line, url: null };
    } 
    // 不是 # 开头且不是空行，且前面有 info 行，那就是 URL 行
    else if (!line.startsWith('#') && currentEntry && currentEntry.info) {
        currentEntry.url = line;
        
        // 判断这个频道属于哪个分类
        let matched = false;
        const combinedText = (currentEntry.info + ' ' + currentEntry.url).toLowerCase();
        
        for (let cat in categories) {
            const keywords = categories[cat];
            if (keywords.some(kw => combinedText.includes(kw.toLowerCase()))) {
                // 写入对应的分类文件
                streams[cat].write(currentEntry.info + '\n');
                streams[cat].write(currentEntry.url + '\n');
                matched = true;
                break;
            }
        }
        
        // 如果没有任何分类匹配，可以写入一个“其他.m3u”（可选，这里暂时忽略）
        currentEntry = null;
    }
}

// 关闭所有文件流
for (let cat in streams) {
    streams[cat].end();
}

console.log('分类完成！已生成以下文件：');
for (let cat in categories) {
    console.log(` - ${cat}`);
}
