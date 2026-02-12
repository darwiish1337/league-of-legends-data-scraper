#!/usr/bin/env python3
"""
Quick Start Script for Riot Games LoL Data Scraper

This script provides a quick way to start scraping with minimal configuration.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from infrastructure import RiotAPIClient
from application import ScrapeMatchesUseCase, ProcessStatisticsUseCase
from domain.enums import Region, QueueType


async def quick_start():
    """Quick start scraping example."""
    print("🚀 Riot Games LoL Data Scraper - Quick Start")
    print("=" * 60)
    
    # Validate API key
    try:
        settings.validate()
        settings.create_directories()
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease set RIOT_API_KEY in your .env file:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your API key: RIOT_API_KEY=RGAPI-your-key-here")
        return
    
    print(f"\n✅ API Key configured")
    print(f"📦 Target Patch: {settings.TARGET_PATCH}")
    print(f"📁 Data Directory: {settings.DATA_DIR}")
    
    # Configuration
    regions = [Region.EUW1]  # Start with one region
    queue_types = [QueueType.RANKED_SOLO_5x5]  # Start with Solo/Duo
    matches_per_region = 100  # Small sample
    
    print("\n" + "-" * 60)
    print("QUICK START CONFIGURATION:")
    print(f"  Region: {regions[0].value}")
    print(f"  Queue: {queue_types[0].queue_name}")
    print(f"  Matches: {matches_per_region}")
    print("-" * 60)
    
    input("\nPress Enter to start scraping...")
    
    # Scrape
    print("\n📥 Collecting matches...")
    
    async with RiotAPIClient(settings.RIOT_API_KEY) as api_client:
        scrape_use_case = ScrapeMatchesUseCase(api_client)
        
        results = await scrape_use_case.execute(
            regions=regions,
            queue_types=queue_types,
            matches_per_region=matches_per_region
        )
        
        # Collect all matches
        all_matches = []
        for region_data in results.values():
            for matches in region_data.values():
                all_matches.extend(matches)
        
        print(f"\n✅ Collected {len(all_matches)} matches!")
        
        if all_matches:
            print("\n📊 Processing statistics...")
            
            process_use_case = ProcessStatisticsUseCase()
            process_use_case.execute(
                matches=all_matches,
                save_db=True,
                export_csv=True
            )
            
            print("\n" + "=" * 60)
            print("✅ QUICK START COMPLETE!")
            print("=" * 60)
            print(f"\nResults saved to:")
            print(f"  DB: {settings.DB_DIR}")
            print(f"  CSV: {settings.CSV_DIR}")
            print("\nTo scrape more data, run: python main.py")
        else:
            print("\n⚠️  No matches collected. Please check:")
            print("  1. Your API key is valid")
            print("  2. You have internet connection")
            print("  3. The patch date range is correct")


if __name__ == "__main__":
    try:
        asyncio.run(quick_start())
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
