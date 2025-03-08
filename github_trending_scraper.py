import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import datetime
import time
import logging
import schedule

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("github_trending_scraper.log"),
        logging.StreamHandler()
    ]
)

def translate_to_chinese(text):
    """将英文描述翻译成中文"""
    if not text:
        return ""
    
    # 使用备用翻译方法，因为googletrans库有兼容性问题
    return translate_fallback(text)

def translate_fallback(text):
    """备用翻译方法，使用HTTP请求方式"""
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
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            try:
                result = response.json()
                translated_text = ''.join([part[0] for part in result[0] if part[0]])
                return translated_text
            except Exception as e:
                logging.error(f"解析翻译响应失败: {e}")
                return text
        else:
            logging.warning(f"翻译请求失败，状态码: {response.status_code}")
            return text
    except Exception as e:
        logging.error(f"备用翻译方法出错: {e}")
        return text

def parse_number(number_str):
    """转换字符串形式的数字（如1.5k）为整数"""
    if not number_str:
        return 0
    
    number_str = number_str.strip().lower()
    if 'k' in number_str:
        return int(float(number_str.replace('k', '')) * 1000)
    elif 'm' in number_str:
        return int(float(number_str.replace('m', '')) * 1000000)
    else:
        try:
            return int(number_str.replace(',', ''))
        except ValueError:
            return 0

def scrape_github_trending():
    """爬取GitHub热门项目数据"""
    url = "https://github.com/trending"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        logging.info("开始爬取GitHub热门项目...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 检查请求是否成功
        
        soup = BeautifulSoup(response.text, 'html.parser')
        repositories = soup.select('article.Box-row')
        
        trending_data = []
        
        for repo in repositories:
            try:
                # 获取项目名称 - 修复选择器
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
                
                # 获取项目描述 - 修复选择器
                description_element = repo.select_one('p.col-9')
                description = description_element.text.strip() if description_element else ""
                
                # 使用备用翻译方法
                chinese_description = translate_fallback(description) if description else ""
                
                # 获取统计数据 (stars, forks) - 修复选择器
                stats = repo.select('a.Link--muted.d-inline-block.mr-3')
                stars = parse_number(stats[0].text.strip()) if len(stats) > 0 else 0
                forks = parse_number(stats[1].text.strip()) if len(stats) > 1 else 0
                
                # 获取当日收藏数 - 修复选择器
                today_stars_element = repo.select_one('span.d-inline-block.float-sm-right')
                if not today_stars_element:
                    today_stars_element = repo.select_one('span.float-right')
                
                today_stars_text = today_stars_element.text.strip() if today_stars_element else "0"
                today_stars = int(''.join(filter(str.isdigit, today_stars_text)) or 0)
                
                repo_data = {
                    "项目名称": full_name,
                    "使用语言": language,
                    "收藏数": stars,
                    "分支数": forks,
                    "描述": description,
                    "中文描述": chinese_description,
                    "当日收藏": today_stars
                }
                
                trending_data.append(repo_data)
                logging.info(f"成功爬取项目: {full_name}")
            except Exception as e:
                logging.error(f"处理仓库数据时出错: {e}")
                continue
        
        return trending_data
    
    except Exception as e:
        logging.error(f"爬取数据时出错: {e}")
        return []

def save_to_csv(data):
    """将数据保存到CSV文件"""
    if not data:
        logging.warning("没有数据可保存")
        return False
    
    try:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        filename = f"github-trending-{today}.csv"
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')  # 使用utf-8-sig确保中文正确显示
        
        logging.info(f"数据已成功保存到 {filename}")
        return True
    
    except Exception as e:
        logging.error(f"保存CSV文件时出错: {e}")
        return False

def job():
    """定时执行的任务"""
    try:
        logging.info("开始执行定时任务...")
        # 爬取GitHub热门项目
        trending_data = scrape_github_trending()
        
        # 保存到CSV
        if trending_data:
            save_to_csv(trending_data)
            logging.info("定时任务完成")
        else:
            logging.warning("未获取到数据")
    
    except Exception as e:
        logging.error(f"定时任务执行过程中出错: {e}")

def main():
    """主函数，设置定时任务"""
    logging.info("GitHub每日热门项目爬虫启动")
    
    # 立即执行一次任务
    job()
    
    # 设置每24小时执行一次
    #schedule.every(24).hours.do(job)
    # 或者在每天特定时间执行，例如每天上午10点
    schedule.every().day.at("10:00").do(job)
    
    logging.info("已设置定时任务，每24小时执行一次")
    
    # 持续运行，等待定时任务
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次是否有待执行的任务

if __name__ == "__main__":
    main()
