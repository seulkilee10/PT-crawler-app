"""
Command Line Interface for TOPIS notice crawler.
"""
import asyncio
import json
import argparse
import sys
from typing import Dict, Any
from pathlib import Path

from ..domain.notice import NoticeCategory
from ..infrastructure.selenium_notice_repository import SeleniumNoticeRepository
from ..application.notice_crawler_service import NoticeCrawlerService


class NoticeCrawlerCLI:
    """Command Line Interface for Notice Crawler."""
    
    def __init__(self):
        """Initialize CLI."""
        self.repository = None
        self.service = None
    
    def _setup_service(self, headless: bool = True) -> None:
        """Setup crawler service.
        
        Args:
            headless: Whether to run browser in headless mode
        """
        self.repository = SeleniumNoticeRepository(headless=headless)
        self.service = NoticeCrawlerService(self.repository)
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        if self.repository:
            self.repository._close_driver()
    
    async def crawl_all(self, output_file: str, max_pages: int = 5, headless: bool = True) -> None:
        """Crawl all categories and save to file.
        
        Args:
            output_file: Output file path
            max_pages: Maximum pages per category
            headless: Whether to run browser in headless mode
        """
        print("🚀 Starting TOPIS Notice Crawler...")
        print(f"📄 Output file: {output_file}")
        print(f"📖 Max pages per category: {max_pages}")
        print(f"👻 Headless mode: {headless}")
        print("=" * 50)
        
        try:
            self._setup_service(headless)
            
            results = await self.service.crawl_all_categories(
                max_pages_per_category=max_pages
            )
            
            # Save results to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            # Print summary
            total_notices = sum(len(notices) for notices in results.values())
            print("=" * 50)
            print("✅ Crawling completed!")
            print(f"📊 Total notices crawled: {total_notices}")
            print(f"💾 Results saved to: {output_file}")
            
            for category, notices in results.items():
                print(f"   - {category}: {len(notices)} notices")
            
        except Exception as e:
            print(f"❌ Error during crawling: {str(e)}")
            sys.exit(1)
        finally:
            self._cleanup()
    
    async def crawl_category_fast(
        self, 
        category_name: str, 
        output_file: str, 
        max_pages: int = 5,
        headless: bool = True
    ) -> None:
        """🚀 Fast crawl specific category with optimizations.
        
        Args:
            category_name: Category name to crawl
            output_file: Output file path
            max_pages: Maximum pages to crawl
            headless: Whether to run browser in headless mode
        """
        # Map category names
        category_mapping = {
            '전체': NoticeCategory.ALL,
            'all': NoticeCategory.ALL,
            '통제안내': NoticeCategory.TRAFFIC_CONTROL,
            'traffic': NoticeCategory.TRAFFIC_CONTROL,
            '버스안내': NoticeCategory.BUS,
            'bus': NoticeCategory.BUS,
            '정책안내': NoticeCategory.POLICY,
            'policy': NoticeCategory.POLICY,
            '기상안내': NoticeCategory.WEATHER,
            'weather': NoticeCategory.WEATHER,
            '기타안내': NoticeCategory.ETC,
            'etc': NoticeCategory.ETC,
        }
        
        if category_name not in category_mapping:
            raise ValueError(f"Unknown category: {category_name}. Available: {list(category_mapping.keys())}")
        
        category = category_mapping[category_name]
        
        try:
            # Setup repository
            repository = SeleniumNoticeRepository(headless=headless)
            service = NoticeCrawlerService(repository)
            
            print("🚀 Starting FAST crawling...")
            print(f"📂 Category: {category_name}")
            print(f"📄 Max pages: {max_pages}")
            print(f"📁 Output: {output_file}")
            print("=" * 50)
            
            # Fast crawling
            notices = await service.crawl_category_fast(category, max_pages=max_pages)
            
            # Convert to dictionaries
            result = []
            for notice in notices:
                notice_dict = {
                    'id': notice.id,
                    'title': notice.title,
                    'category': service._get_category_name(notice.category),
                    'created_date': notice.created_date.isoformat(),
                    'view_count': notice.view_count,
                    'has_attachment': notice.has_attachment,
                    'content': notice.content
                }
                result.append(notice_dict)
            
            # Save results to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print("🎉 Fast crawling completed!")
            print(f"📊 Total notices: {len(result)}")
            print(f"💾 Saved to: {output_file}")
            
        except Exception as e:
            print(f"❌ Fast crawling failed: {str(e)}")
            raise
        finally:
            self._cleanup()
    
    async def crawl_category(
        self, 
        category_name: str, 
        output_file: str, 
        max_pages: int = 5,
        with_content: bool = False,
        headless: bool = True
    ) -> None:
        """Crawl specific category.
        
        Args:
            category_name: Category name to crawl
            output_file: Output file path
            max_pages: Maximum pages to crawl
            with_content: Whether to get full content
            headless: Whether to run browser in headless mode
        """
        # Map category names
        category_mapping = {
            '전체': NoticeCategory.ALL,
            'all': NoticeCategory.ALL,
            '통제안내': NoticeCategory.TRAFFIC_CONTROL,
            'traffic': NoticeCategory.TRAFFIC_CONTROL,
            '버스안내': NoticeCategory.BUS,
            'bus': NoticeCategory.BUS,
            '정책안내': NoticeCategory.POLICY,
            'policy': NoticeCategory.POLICY,
            '기상안내': NoticeCategory.WEATHER,
            'weather': NoticeCategory.WEATHER,
            '기타안내': NoticeCategory.ETC,
            'etc': NoticeCategory.ETC
        }
        
        category = category_mapping.get(category_name.lower())
        if not category:
            print(f"❌ Invalid category: {category_name}")
            print(f"Available categories: {', '.join(category_mapping.keys())}")
            sys.exit(1)
        
        print("🚀 Starting TOPIS Notice Crawler...")
        print(f"📂 Category: {category_name}")
        print(f"📄 Output file: {output_file}")
        print(f"📖 Max pages: {max_pages}")
        print(f"📝 With content: {with_content}")
        print(f"👻 Headless mode: {headless}")
        print("=" * 50)
        
        try:
            self._setup_service(headless)
            
            if with_content:
                results = await self.service.crawl_with_content(category, max_notices=50)
            else:
                notices = await self.service.crawl_category(category, max_pages)
                # Convert to dict format
                results = []
                for notice in notices:
                    notice_dict = {
                        'id': notice.id,
                        'title': notice.title,
                        'category': self.service._get_category_name(notice.category),
                        'created_date': notice.created_date.isoformat(),
                        'view_count': notice.view_count,
                        'has_attachment': notice.has_attachment,
                        'content': notice.content
                    }
                    results.append(notice_dict)
            
            # Save results to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            # Print summary
            print("=" * 50)
            print("✅ Crawling completed!")
            print(f"📊 Total notices crawled: {len(results)}")
            print(f"💾 Results saved to: {output_file}")
            
        except Exception as e:
            print(f"❌ Error during crawling: {str(e)}")
            sys.exit(1)
        finally:
            self._cleanup()
    
    async def get_notice_detail(self, notice_id: str, output_file: str, headless: bool = True) -> None:
        """Get detail of a specific notice.
        
        Args:
            notice_id: ID of the notice to get
            output_file: Output file path
            headless: Whether to run browser in headless mode
        """
        print("🚀 Getting notice detail...")
        print(f"🆔 Notice ID: {notice_id}")
        print(f"📄 Output file: {output_file}")
        print("=" * 50)
        
        try:
            self._setup_service(headless)
            
            result = await self.service.get_notice_with_content(notice_id)
            
            if result:
                # Save results to file
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                print("✅ Notice detail retrieved!")
                print(f"📄 Title: {result['title']}")
                print(f"📂 Category: {result['category']}")
                print(f"💾 Results saved to: {output_file}")
            else:
                print(f"❌ Notice {notice_id} not found")
                sys.exit(1)
            
        except Exception as e:
            print(f"❌ Error getting notice detail: {str(e)}")
            sys.exit(1)
        finally:
            self._cleanup()
    
    async def get_statistics(self, headless: bool = True) -> None:
        """Get statistics about notices.
        
        Args:
            headless: Whether to run browser in headless mode
        """
        print("🚀 Getting TOPIS notice statistics...")
        print("=" * 50)
        
        try:
            self._setup_service(headless)
            
            stats = await self.service.get_statistics()
            
            print("📊 Notice Statistics:")
            print(f"🔢 Estimated total notices: {stats['total_notices']}")
            print()
            
            for category, category_stats in stats['categories'].items():
                print(f"📂 {category}:")
                if 'error' in category_stats:
                    print(f"   ❌ Error: {category_stats['error']}")
                else:
                    print(f"   📄 Estimated total: {category_stats['estimated_total']}")
                    print(f"   📖 Total pages: {category_stats['total_pages']}")
                    print(f"   🔍 Sample notices: {category_stats['sample_notices']}")
                print()
            
        except Exception as e:
            print(f"❌ Error getting statistics: {str(e)}")
            sys.exit(1)
        finally:
            self._cleanup()

    async def crawl_with_date_filter(
        self,
        category_name: str,
        output_file: str,
        start_date: str = None,
        end_date: str = None,
        max_pages: int = 5,
        with_content: bool = False,
        headless: bool = True
    ) -> None:
        """날짜 필터로 크롤링.
        
        Args:
            category_name: 카테고리 이름
            output_file: 출력 파일 경로
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            max_pages: 최대 페이지 수
            with_content: 상세 내용 포함 여부
            headless: 헤드리스 모드 여부
        """
        from ..domain.date_filter import DateFilter
        from datetime import datetime
        
        # 날짜 파싱
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
        
        date_filter = DateFilter(start_date=start_dt, end_date=end_dt)
        
        print("🚀 Starting TOPIS Notice Crawler with Date Filter...")
        print(f"📂 Category: {category_name}")
        print(f"📅 Date Filter: {date_filter}")
        print(f"📄 Output file: {output_file}")
        print("=" * 50)
        
        # 기존 크롤링 로직 실행
        await self.crawl_category(
            category_name, output_file, max_pages, with_content, headless
        )
        
        # 날짜 필터링 적용
        if start_dt or end_dt:
            print("📅 Applying date filter...")
            
            output_path = Path(output_file)
            with open(output_path, 'r', encoding='utf-8') as f:
                notices = json.load(f)
            
            filtered_notices = []
            for notice in notices:
                notice_date = datetime.fromisoformat(notice['created_date'])
                if date_filter.is_in_range(notice_date):
                    filtered_notices.append(notice)
            
            # 필터된 결과 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(filtered_notices, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Date filtering completed! {len(filtered_notices)}/{len(notices)} notices match the criteria.")

    async def export_to_word(
        self,
        notice_id: str,
        output_file: str,
        headless: bool = True
    ) -> None:
        """공지사항을 Word 문서로 내보내기.
        
        Args:
            notice_id: 공지사항 ID
            output_file: 출력 파일 경로
            headless: 헤드리스 모드 여부
        """
        from ..application.word_export_service import WordExportService
        
        print("🚀 Exporting notice to Word document...")
        print(f"🆔 Notice ID: {notice_id}")
        print(f"📄 Output file: {output_file}")
        print("=" * 50)
        
        try:
            self._setup_service(headless)
            
            # 공지사항 상세 정보 가져오기
            notice_dict = await self.service.get_notice_with_content(notice_id)
            
            if not notice_dict:
                print(f"❌ Notice {notice_id} not found")
                sys.exit(1)
            
            # Word 문서 생성
            word_service = WordExportService()
            word_service.create_notice_document(notice_dict, output_file)
            
            print("✅ Word document created successfully!")
            print(f"📄 Title: {notice_dict['title']}")
            print(f"📂 Category: {notice_dict['category']}")
            print(f"💾 File saved to: {output_file}")
            
        except Exception as e:
            print(f"❌ Error exporting to Word: {str(e)}")
            sys.exit(1)
        finally:
            self._cleanup()

    def serve_web(self, host: str = '127.0.0.1', port: int = 8080, debug: bool = False, board_style: bool = False) -> None:
        """웹 서버 실행."""
        if board_style:
            from ..interface_adapters.board_web_server import run_server
        else:
            from ..interface_adapters.web_server import run_server
        run_server(host=host, port=port, debug=debug)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='TOPIS Seoul Traffic Notice Crawler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Crawl all categories
  python main.py crawl-all -o results/all_notices.json

  # Crawl specific category (normal)
  python main.py crawl-category 버스안내 -o results/bus_notices.json
  
  # Fast crawling (⚡ 3-5x faster!)
  python main.py crawl-fast 통제안내 -o results/traffic_fast.json --max-pages 3

  # Crawl with date filter
  python main.py crawl-date 통제안내 -o results/traffic.json --start-date 2025-09-01 --end-date 2025-09-15

  # Export notice to Word document
  python main.py export-word 5284 -o documents/notice_5284.docx

  # Start web server (recommended!)
  python main.py serve
  
  # Start board-style web server (new!)
  python main.py serve --board --port 8080

  # Get specific notice detail
  python main.py get-detail 5284 -o results/notice_5284.json

  # Get statistics
  python main.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Crawl all command
    crawl_all_parser = subparsers.add_parser('crawl-all', help='Crawl all categories')
    crawl_all_parser.add_argument('-o', '--output', required=True, help='Output JSON file')
    crawl_all_parser.add_argument('--max-pages', type=int, default=5, help='Max pages per category')
    crawl_all_parser.add_argument('--no-headless', action='store_true', help='Run browser with GUI')
    
    # Crawl category command
    crawl_cat_parser = subparsers.add_parser('crawl-category', help='Crawl specific category')
    crawl_cat_parser.add_argument('category', help='Category name (전체, 통제안내, 버스안내, 정책안내, 기상안내, 기타안내)')
    crawl_cat_parser.add_argument('-o', '--output', required=True, help='Output JSON file')
    crawl_cat_parser.add_argument('--max-pages', type=int, default=5, help='Max pages to crawl')
    crawl_cat_parser.add_argument('--with-content', action='store_true', help='Get full content (slower)')
    crawl_cat_parser.add_argument('--no-headless', action='store_true', help='Run browser with GUI')
    
    # Fast crawl command (⚡ optimized)
    fast_parser = subparsers.add_parser('crawl-fast', help='🚀 Fast crawl (3-5x faster)')
    fast_parser.add_argument('category', help='Category name (전체, 통제안내, 버스안내, 정책안내, 기상안내, 기타안내)')
    fast_parser.add_argument('-o', '--output', required=True, help='Output JSON file')
    fast_parser.add_argument('--max-pages', type=int, default=3, help='Max pages to crawl (default: 3 for speed)')
    fast_parser.add_argument('--no-headless', action='store_true', help='Run browser with GUI')
    
    # Get detail command
    detail_parser = subparsers.add_parser('get-detail', help='Get specific notice detail')
    detail_parser.add_argument('notice_id', help='Notice ID')
    detail_parser.add_argument('-o', '--output', required=True, help='Output JSON file')
    detail_parser.add_argument('--no-headless', action='store_true', help='Run browser with GUI')
    
    # Statistics command
    stats_parser = subparsers.add_parser('stats', help='Get notice statistics')
    stats_parser.add_argument('--no-headless', action='store_true', help='Run browser with GUI')
    
    # Date-filtered crawl command
    date_crawl_parser = subparsers.add_parser('crawl-date', help='Crawl with date filter')
    date_crawl_parser.add_argument('category', help='Category name')
    date_crawl_parser.add_argument('-o', '--output', required=True, help='Output JSON file')
    date_crawl_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    date_crawl_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    date_crawl_parser.add_argument('--max-pages', type=int, default=5, help='Max pages to crawl')
    date_crawl_parser.add_argument('--with-content', action='store_true', help='Get full content')
    date_crawl_parser.add_argument('--no-headless', action='store_true', help='Run browser with GUI')
    
    # Word export command
    word_parser = subparsers.add_parser('export-word', help='Export notice to Word')
    word_parser.add_argument('notice_id', help='Notice ID')
    word_parser.add_argument('-o', '--output', required=True, help='Output Word file')
    word_parser.add_argument('--no-headless', action='store_true', help='Run browser with GUI')
    
    # Web server command
    serve_parser = subparsers.add_parser('serve', help='Start web server')
    serve_parser.add_argument('--host', default='127.0.0.1', help='Server host')
    serve_parser.add_argument('--port', type=int, default=8080, help='Server port')
    serve_parser.add_argument('--debug', action='store_true', help='Debug mode')
    serve_parser.add_argument('--board', action='store_true', help='Use board-style UI')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    cli = NoticeCrawlerCLI()
    
    try:
        if args.command == 'crawl-all':
            asyncio.run(cli.crawl_all(
                output_file=args.output,
                max_pages=args.max_pages,
                headless=not args.no_headless
            ))
        elif args.command == 'crawl-category':
            asyncio.run(cli.crawl_category(
                category_name=args.category,
                output_file=args.output,
                max_pages=args.max_pages,
                with_content=args.with_content,
                headless=not args.no_headless
            ))
        elif args.command == 'crawl-fast':
            # 🚀 빠른 크롤링 실행
            asyncio.run(cli.crawl_category_fast(
                category_name=args.category,
                output_file=args.output,
                max_pages=args.max_pages,
                headless=not args.no_headless
            ))
        elif args.command == 'get-detail':
            asyncio.run(cli.get_notice_detail(
                notice_id=args.notice_id,
                output_file=args.output,
                headless=not args.no_headless
            ))
        elif args.command == 'stats':
            asyncio.run(cli.get_statistics(
                headless=not args.no_headless
            ))
        elif args.command == 'crawl-date':
            asyncio.run(cli.crawl_with_date_filter(
                category_name=args.category,
                output_file=args.output,
                start_date=args.start_date,
                end_date=args.end_date,
                max_pages=args.max_pages,
                with_content=args.with_content,
                headless=not args.no_headless
            ))
        elif args.command == 'export-word':
            asyncio.run(cli.export_to_word(
                notice_id=args.notice_id,
                output_file=args.output,
                headless=not args.no_headless
            ))
        elif args.command == 'serve':
            cli.serve_web(
                host=args.host,
                port=args.port,
                debug=args.debug,
                board_style=args.board
            )
    except KeyboardInterrupt:
        print("\n⏹️ Crawling stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
