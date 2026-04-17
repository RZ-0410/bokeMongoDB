#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
博客系统 - 真实数据导入脚本
将CSV文件数据导入到MongoDB和MySQL数据库
"""

import pandas as pd
import json
from datetime import datetime
from pymongo import MongoClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import random
import sys
import os
# MongoDB连接
print("正在连接MongoDB...")
mongo_client = MongoClient('mongodb://localhost:27017/')
mongo_db = mongo_client['    ']

# MySQL连接
print("正在连接MySQL...")
mysql_engine = create_engine('mysql+pymysql://root:123456@localhost/')
MySQLSession = sessionmaker(bind=mysql_engine)

# MongoDB集合
articles_collection = mongo_db['articles']
categories_collection = mongo_db['categories']
users_collection = mongo_db['users']

# 文章内容生成函数
def generate_content(title, category):
    """根据标题和分类生成文章内容"""
    base_contents = {
        'Python': [
            'Python是一种广泛使用的高级编程语言，属于通用型编程语言，可以应用于多种领域。',
            'Python的设计哲学强调代码的可读性和简洁的语法。',
            '相比于C++或Java，Python让开发者能够用更少的代码表达想法。',
            '不管是小型还是大型程序，该语言都试图让程序的结构清晰明了。',
            'Python支持多种编程范式，包括面向对象、命令式、函数式和过程式编程。'
        ],
        'JavaScript': [
            'JavaScript是一种高级的、解释型的编程语言。',
            'JavaScript是一门基于原型、函数先行的语言，是一门多范式的语言。',
            '它支持面向对象编程、命令式编程以及函数式编程。',
            'JavaScript最初被创建用于使网页具有交互性。',
            '随着Node.js的出现，JavaScript也可以用于服务器端编程。'
        ],
        '数据库': [
            '数据库是"按照数据结构来组织、存储和管理数据的仓库"。',
            '是一个长期存储在计算机内的、有组织的、可共享的、统一管理的大量数据的集合。',
            '数据库中的数据按一定的数据模型组织、描述和存储。',
            '具有较小的冗余度、较高的数据独立性和易扩展性。',
            '常见的数据库包括关系型数据库和NoSQL数据库。'
        ],
        'React': [
            'React是一个用于构建用户界面的JavaScript库。',
            'React主要用于构建UI，很多人认为React是MVC中的V（视图）。',
            'React起源于Facebook的内部项目，用来架设Instagram的网站。',
            'React拥有较高的性能，代码逻辑非常简单。',
            'React使用虚拟DOM来提高渲染性能。'
        ],
        'Vue': [
            'Vue是一套用于构建用户界面的渐进式框架。',
            'Vue被设计为可以自底向上逐层应用。',
            'Vue的核心库只关注视图层，不仅易于上手，还便于与第三方库或既有项目进行整合。',
            'Vue完全有能力驱动采用单文件组件和Vue生态系统支持的库开发的复杂单页应用。',
            'Vue的响应式数据绑定和组合式API让开发更加高效。'
        ],
        'Node.js': [
            'Node.js是一个基于Chrome V8引擎的JavaScript运行环境。',
            'Node.js使用了一个事件驱动、非阻塞式I/O的模型，使其轻量又高效。',
            'Node.js的包生态系统npm是全球最大的开源库生态系统。',
            'Node.js可以用于开发服务器端应用、命令行工具等。',
            'Node.js的异步编程模型使其特别适合高并发的网络应用。'
        ],
        'CSS': [
            'CSS（层叠样式表）是一种用来为结构化文档添加样式的计算机语言。',
            'CSS不仅可以静态地修饰网页，还可以配合各种脚本语言动态地对网页各元素进行格式化。',
            'CSS能够对网页中元素位置的排版进行像素级精确控制。',
            'CSS3引入了许多新特性，如动画、变换、过渡等。',
            'Flexbox和Grid布局让CSS布局变得更加简单和强大。'
        ],
        'TypeScript': [
            'TypeScript是JavaScript的一个超集，它添加了可选的静态类型和基于类的面向对象编程。',
            'TypeScript由Microsoft开发和维护。',
            'TypeScript可以编译成纯JavaScript，在任何浏览器、任何计算机和任何操作系统上运行。',
            'TypeScript的类型系统让代码更加健壮，减少了运行时错误。',
            'TypeScript支持最新的JavaScript特性，并提供向下兼容。'
        ],
        '算法': [
            '算法是指解题方案的准确而完整的描述，是一系列解决问题的清晰指令。',
            '算法代表着用系统的方法描述解决问题的策略机制。',
            '数据结构是计算机存储、组织数据的方式。',
            '不同种类的数据结构适合于不同种类的应用。',
            '算法和数据结构是计算机科学的基础，对编程至关重要。'
        ]
    }
    
    # 获取基础内容
    if category in base_contents:
        content_list = base_contents[category]
    else:
        content_list = base_contents['Python']  # 默认内容
    
    # 生成内容
    content = f"【{title}】\n\n"
    content += '\n\n'.join(random.sample(content_list, min(len(content_list), 3)))
    content += f"\n\n本文详细介绍了{title}的相关内容，希望对读者有所帮助。"
    
    return content


def import_csv_to_databases(csv_file_path):
    """将CSV数据导入到MongoDB和MySQL"""
    try:
        print(f"\n正在读取CSV文件: {csv_file_path}")

        # 尝试多种编码方案
        encodings = [
            'utf-8-sig',  # UTF-8 with BOM (Windows常见)
            'gb18030',  # GBK的超集，支持更多中文字符
            'cp936',  # Windows简体中文
            'latin1',  # 能处理任何字节，但可能有乱码
            'utf-8'  # 标准UTF-8
        ]

        df = None
        successful_encoding = None

        for encoding in encodings:
            try:
                print(f"  尝试使用 {encoding} 编码读取...")
                # 使用Python引擎处理复杂编码
                df = pd.read_csv(csv_file_path, encoding=encoding, engine='python')
                successful_encoding = encoding
                print(f"  ✓ 成功使用 {encoding} 编码读取文件")
                break
            except UnicodeDecodeError as e:
                print(f"  ✗ {encoding} 编码失败: {str(e)[:60]}...")
                continue
            except Exception as e:
                print(f"  ✗ {encoding} 编码发生错误: {str(e)[:60]}...")
                continue

        # 如果所有编码都失败，尝试用Python内置open处理
        if df is None:
            print("  尝试使用Python内置open函数处理编码...")
            try:
                with open(csv_file_path, 'r', encoding='utf-8', errors='replace') as f:
                    df = pd.read_csv(f, engine='python')
                successful_encoding = 'utf-8 (with errors=replace)'
                print("  ✓ 成功使用Python内置open读取")
            except Exception as e:
                print(f"  ✗ Python内置open读取失败: {str(e)}")

                # 最后尝试：用latin1编码（可以处理任何字节）
                try:
                    df = pd.read_csv(csv_file_path, encoding='latin1', engine='python')
                    successful_encoding = 'latin1'
                    print("  ✓ 成功使用latin1编码读取（可能有乱码）")
                    # 记录警告
                    print("  ⚠️  警告：使用latin1编码可能导致部分中文显示为乱码")
                except Exception as e:
                    print(f"\n❌ 无法读取CSV文件: {str(e)}")
                    print("\n请尝试以下方法:")
                    print("1. 用Notepad++或VSCode打开CSV文件")
                    print("2. 查看文件的实际编码（状态栏通常会显示）")
                    print("3. 将文件另存为UTF-8格式后重试")
                    return False

        print(f"\n✓ 成功读取CSV文件，共 {len(df)} 条记录")
        print(f"  使用编码: {successful_encoding}")

        # ... 其余代码保持不变 ...
        # 清空现有数据
        print("正在清空现有数据...")
        articles_collection.delete_many({})
        categories_collection.delete_many({})
        print("✓ MongoDB数据已清空\n")
        
        # 清空MySQL表
        with MySQLSession() as session:
            session.execute(text("DELETE FROM comments"))
            session.execute(text("DELETE FROM authors"))
            session.commit()
        print("✓ MySQL数据已清空\n")
        
        # 记录分类信息
        main_categories = set()
        sub_categories = set()
        authors = set()
        
        # 处理数据
        articles = []
        author_records = []
        
        print("开始处理数据...")
        for index, row in df.iterrows():
            try:
                # 解析发布时间
                publish_time = None
                if pd.notna(row.get('publish_time')):
                    try:
                        publish_time = datetime.strptime(str(row['publish_time']), '%Y-%m-%d %H:%M:%S')
                    except:
                        try:
                            publish_time = datetime.strptime(str(row['publish_time']), '%Y-%m-%d')
                        except:
                            publish_time = datetime.now()
                else:
                    publish_time = datetime.now()
                
                # 生成文章内容
                content = generate_content(
                    str(row.get('title', f'文章{index + 1}')),
                    str(row.get('main_category', '技术'))
                )
                
                # 构建文章数据
                article = {
                    'title': str(row.get('title', f'文章{index + 1}')),
                    'author': str(row.get('author', '匿名作者')),
                    'author_url': str(row.get('author_url', '')),
                    'main_category': str(row.get('main_category', '技术')),
                    'sub_category': str(row.get('sub_category', '编程')),
                    'content': content,
                    'url': str(row.get('url', '')),
                    'publish_time': publish_time,
                    'read_count': int(row.get('read_count', random.randint(100, 10000))),
                    'like_count': int(row.get('like_count', random.randint(10, 1000))),
                    'collect_count': int(row.get('collect_count', random.randint(5, 500))),
                    'comment_count': 0,
                    'content_length': len(content),
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                
                articles.append(article)
                
                # 记录分类
                main_categories.add(article['main_category'])
                sub_categories.add(article['sub_category'])
                authors.add(article['author'])
                
                # 记录作者信息
                author_records.append({
                    'username': article['author'],
                    'author_url': article['author_url'],
                    'fans_count': int(row.get('fans_count', random.randint(100, 10000)))
                })
                
                if (index + 1) % 10 == 0:
                    print(f"  已处理 {index + 1} 条数据...")
                    
            except Exception as e:
                print(f"  ⚠ 处理第 {index + 1} 行数据时出错: {e}")
                continue
        
        print(f"\n✓ 数据处理完成，共 {len(articles)} 篇文章\n")
        
        # 插入文章到MongoDB
        print("正在插入文章到MongoDB...")
        if articles:
            result = articles_collection.insert_many(articles)
            print(f"✓ 成功插入 {len(result.inserted_ids)} 篇文章\n")
        
        # 保存主分类到MongoDB
        print("正在保存分类信息...")
        for category in main_categories:
            categories_collection.insert_one({
                'name': category,
                'type': 'main',
                'created_at': datetime.now()
            })
        
        # 保存子分类到MongoDB
        for sub_category in sub_categories:
            categories_collection.insert_one({
                'name': sub_category,
                'type': 'sub',
                'created_at': datetime.now()
            })
        
        print(f"✓ 已保存 {len(main_categories)} 个主分类")
        print(f"✓ 已保存 {len(sub_categories)} 个子分类\n")
        
        # 保存作者信息到MySQL
        print("正在保存作者信息到MySQL...")
        with MySQLSession() as session:
            for author_data in author_records:
                try:
                    session.execute(
                        text("""
                            INSERT INTO authors (username, author_url, fans_count, created_at)
                            VALUES (:username, :author_url, :fans_count, :created_at)
                            ON DUPLICATE KEY UPDATE
                            author_url = VALUES(author_url),
                            fans_count = VALUES(fans_count)
                        """),
                        {
                            'username': author_data['username'],
                            'author_url': author_data['author_url'],
                            'fans_count': author_data['fans_count'],
                            'created_at': datetime.now()
                        }
                    )
                except Exception as e:
                    print(f"  ⚠ 保存作者 {author_data['username']} 时出错: {e}")
                    continue
            session.commit()
        
        print(f"✓ 成功保存 {len(authors)} 个作者信息\n")
        
        # 创建索引
        print("正在创建数据库索引...")
        articles_collection.create_index('title')
        articles_collection.create_index('author')
        articles_collection.create_index('main_category')
        articles_collection.create_index('sub_category')
        articles_collection.create_index('publish_time')
        articles_collection.create_index('like_count')
        articles_collection.create_index('collect_count')
        print("✓ 索引创建完成\n")
        
        # 显示统计信息
        print(f"{'='*50}")
        print("数据导入完成！")
        print(f"{'='*50}\n")
        
        total_articles = articles_collection.count_documents({})
        total_categories = categories_collection.count_documents({'type': 'main'})
        total_sub_categories = categories_collection.count_documents({'type': 'sub'})
        
        print("📊 数据库统计:")
        print(f"  - 文章总数: {total_articles}")
        print(f"  - 主分类数: {total_categories}")
        print(f"  - 子分类数: {total_sub_categories}")
        print(f"  - 作者数: {len(authors)}")
        
        # 显示分类列表
        print(f"\n📂 主分类列表:")
        for category in sorted(main_categories):
            print(f"  - {category}")
        
        print(f"\n📂 子分类列表:")
        for sub_category in sorted(sub_categories):
            print(f"  - {sub_category}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 导入数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_import():
    """验证数据导入结果"""
    print(f"\n{'='*50}")
    print("验证数据导入结果")
    print(f"{'='*50}\n")
    
    try:
        # 检查MongoDB数据
        print("MongoDB 数据检查:")
        print(f"  - 文章数量: {articles_collection.count_documents({})}")
        print(f"  - 分类数量: {categories_collection.count_documents({})}")
        
        # 显示前几篇文章
        print(f"\n  前3篇文章:")
        for i, article in enumerate(articles_collection.find().limit(3), 1):
            print(f"    {i}. {article['title']} - {article['author']}")
        
        # 检查MySQL数据
        print(f"\nMySQL 数据检查:")
        with MySQLSession() as session:
            author_count = session.execute(text("SELECT COUNT(*) FROM authors")).scalar()
            print(f"  - 作者数量: {author_count}")
            
            comment_count = session.execute(text("SELECT COUNT(*) FROM comments")).scalar()
            print(f"  - 评论数量: {comment_count}")
            
            # 显示前3个作者
            print(f"\n  前3个作者:")
            authors = session.execute(text("SELECT username, fans_count FROM authors LIMIT 3"))
            for i, author in enumerate(authors, 1):
                print(f"    {i}. {author.username} - {author.fans_count} 粉丝")
        
        print(f"\n{'='*50}")
        print("✓ 数据验证完成")
        print(f"{'='*50}\n")
        
    except Exception as e:
        print(f"❌ 验证数据时出错: {e}")

if __name__ == '__main__':
    csv_file = 'csdn_data.csv'
    
    print(f"\n{'='*50}")
    print("博客系统 - 数据导入工具")
    print(f"{'='*50}\n")
    
    print(f"CSV文件路径: {csv_file}")
    
    # 检查文件是否存在
    if not os.path.exists(csv_file):
        print(f"\n❌ 错误: CSV文件不存在: {csv_file}")
        print("\n使用方法:")
        print("  python import_real_data.py")
        print("  或")
        print("  python import_real_data.py <csv_file_path>")
        sys.exit(1)
    
    # 导入数据
    success = import_csv_to_databases(csv_file)
    
    if success:
        # 验证导入结果
        verify_import()
        print("\n🎉 数据导入成功！现在可以启动博客系统了。")
        print("\n启动命令:")
        print("  python app.py")
        print("  或")
        print("  bash run.sh")
    else:
        print("\n❌ 数据导入失败，请检查错误信息。")
        sys.exit(1)
