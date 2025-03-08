import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import time
import logging
from functools import lru_cache
import schedule
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("github_trending_scraper.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 使用LRU缓存装饰器优化翻译函数，避免重复翻译相同文本
@lru_cache(maxsize=128)
def translate_to_chinese(text: str) -> str:
    """将英文描述翻译成中文
    
    Args:
        text: 需要翻译的英文文本
        
    Returns:
        翻译后的中文文本
    """
    if not text:
        return ""
    
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "en",
            "tl": "zh-CN",
            "dt": "t",
            "q": text
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            try:
                result = response.json()
                translated_text = ''.join([part[0] for part in result[0] if part[0]])
                return translated_text
            except Exception as e:
                logger.error(f"解析翻译响应失败: {e}")
                return text
        else:
            logger.warning(f"翻译请求失败，状态码: {response.status_code}")
            return text
    except Exception as e:
        logger.error(f"翻译过程出错: {e}")
        return text


def parse_number(number_str: Optional[str]) -> int:
    """转换字符串形式的数字（如1.5k）为整数
    
    Args:
        number_str: 包含数字的字符串，可能包含k或m等单位
        
    Returns:
        转换后的整数值
    """
    if not number_str:
        return 0
    
    number_str = number_str.strip().lower()
    try:
        if 'k' in number_str:
            return int(float(number_str.replace('k', '')) * 1000)
        elif 'm' in number_str:
            return int(float(number_str.replace('m', '')) * 1000000)
        else:
            return int(number_str.replace(',', ''))
    except (ValueError, TypeError):
        return 0


def extract_repo_data(repo) -> Dict[str, Any]:
    """从仓库HTML元素中提取数据
    
    Args:
        repo: BeautifulSoup元素，表示一个GitHub仓库
        
    Returns:
        包含仓库信息的字典
    """
    # 获取项目名称
    name_element = repo.select_one('h2.h3 a')
    if name_element:
        full_name = name_element.text.strip().replace("\n", "").replace(" ", "")
    else:
        # 备用方法
        name_parts = repo.select('h2.h3 a span')
        full_name = '/'.join([span.text.strip() for span in name_parts if span.text.strip()])
    
    # 获取语言
    language_element = repo.select_one('span[itemprop="programmingLanguage"]')
    language = language_element.text.strip() if language_element else "未指定"
    
    # 获取项目描述
    description_element = repo.select_one('p.col-9')
    description = description_element.text.strip() if description_element else ""
    
    # 使用缓存翻译方法
    chinese_description = translate_to_chinese(description) if description else ""
    
    # 获取统计数据 (stars, forks)
    stats = repo.select('a.Link--muted.d-inline-block.mr-3')
    stars = parse_number(stats[0].text.strip()) if len(stats) > 0 else 0
    forks = parse_number(stats[1].text.strip()) if len(stats) > 1 else 0
    
    # 获取当日收藏数
    today_stars_element = repo.select_one('span.d-inline-block.float-sm-right') or repo.select_one('span.float-right')
    today_stars_text = today_stars_element.text.strip() if today_stars_element else "0"
    today_stars = int(''.join(filter(str.isdigit, today_stars_text)) or 0)
    
    return {
        "项目名称": full_name,
        "使用语言": language,
        "收藏数": stars,
        "分支数": forks,
        "描述": description,
        "中文描述": chinese_description,
        "当日收藏": today_stars
    }


def scrape_github_trending(timeout: int = 30) -> List[Dict[str, Any]]:
    """爬取GitHub热门项目数据
    
    Args:
        timeout: 请求超时时间（秒）
        
    Returns:
        包含GitHub热门项目信息的列表
    """
    url = "https://github.com/trending"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        logger.info("开始爬取GitHub热门项目...")
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        repositories = soup.select('article.Box-row')
        
        trending_data = []
        
        # 使用线程池并行处理每个仓库数据
        with ThreadPoolExecutor(max_workers=5) as executor:
            trending_data = list(filter(None, executor.map(
                lambda repo: extract_repo_data(repo), 
                repositories
            )))
        
        logger.info(f"成功爬取 {len(trending_data)} 个热门项目")
        return trending_data
    
    except requests.RequestException as e:
        logger.error(f"请求GitHub时出错: {e}")
        return []
    except Exception as e:
        logger.error(f"爬取数据时出错: {e}")
        return []


def save_to_csv(data: List[Dict[str, Any]]) -> bool:
    """将数据保存到CSV文件
    
    Args:
        data: 要保存的数据列表
        
    Returns:
        保存成功返回True，否则返回False
    """
    if not data:
        logger.warning("没有数据可保存")
        return False
    
    try:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        filename = f"github-trending-{today}.csv"
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        logger.info(f"数据已成功保存到 {filename}")
        return True
    
    except Exception as e:
        logger.error(f"保存CSV文件时出错: {e}")
        return False


def job() -> None:
    """定时执行的爬虫任务"""
    try:
        logger.info("开始执行定时爬虫任务...")
        # 设置重试机制
        max_retries = 3
        for attempt in range(max_retries):
            trending_data = scrape_github_trending()
            if trending_data:
                save_to_csv(trending_data)
                logger.info("定时任务完成")
                break
            else:
                if attempt < max_retries - 1:
                    retry_delay = 60 * (attempt + 1)  # 递增重试间隔
                    logger.warning(f"第 {attempt + 1} 次尝试未获取到数据，将在 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"已尝试 {max_retries} 次，仍未获取到数据，任务失败")
    
    except Exception as e:
        logger.error(f"定时任务执行过程中出错: {e}")


def main() -> None:
    """主函数，设置定时任务"""
    logger.info("GitHub每日热门项目爬虫启动")
    
    # 立即执行一次任务
    job()
    
    # 设置定时任务 - 每天10点执行
    schedule.every().day.at("10:00").do(job)
    logger.info("已设置定时任务，每天10:00执行")
    
    try:
        # 持续运行，等待定时任务
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次是否有待执行的任务
    except KeyboardInterrupt:
        logger.info("爬虫程序已手动停止")
    except Exception as e:
        logger.critical(f"爬虫程序意外终止: {e}")


if __name__ == "__main__":
    main()
