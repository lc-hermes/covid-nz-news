# COVID NZ News - Review and Improvements

## Current State Analysis

### What's Working ✅
1. **Modular architecture** - Clean separation of concerns
2. **Memory-safe** - Streaming WARC parsing (no more 5GB file loads)
3. **Type-safe** - Full type annotations, ty passes
4. **Linted** - Ruff clean
5. **Configurable** - Environment variables + .env.example
6. **CI/CD** - GitHub Actions with ruff + ty checks
7. **Logging** - Proper logging throughout
8. **Retry logic** - Exponential backoff for network failures

### Critical Issues ❌

#### 1. **Limited News Sources** (HIGH PRIORITY)
**Current**: Only `*.nzherald.co.nz/` (single source)
**Problem: This is NOT sufficient for a COVID salience timeline)

**Major NZ news sources missing**:
- `*.stuff.co.nz/` - Stuff (largest NZ news site)
- `*.nzherald.co.nz/` - NZ Herald (currently included)
- `*.newsroom.co.nz/` - Newsroom
- `*.tvnz.co.nz/` - TVNZ
- `*.3news.co.nz/` - 3News
- `*.one-news.co.nz/` - One News
- `*.radio.co.nz/` - Radio NZ
- `*.stuff.co.nz/` - Stuff.co.nz
- `*.bloomberg.com/news/.../new-zealand` - International coverage
- `*.rnz.co.nz/` - RNZ (public broadcaster)

**Impact**: Cannot create a representative COVID salience timeline with just one source. Need 5-10 major sources.

#### 2. **No Date Range Filtering** (HIGH PRIORITY)
**Current**: No way to filter by date range
**Problem**: COVID timeline spans 2020-2022, but we're pulling from CC-MAIN-2020-16 which is just April 2020
**Need**: Ability to specify date ranges per crawl (CC-MAIN-2020-XX through CC-MAIN-2022-XX)

#### 3. **No Timestamp Extraction from Content** (MEDIUM PRIORITY)
**Current**: Only using WARC timestamp (crawl time, not publish time)
**Problem**: Cannot create accurate timeline if article publish date differs from crawl date
**Need**: Extract publish date from article HTML (meta tags, date elements)

#### 4. **Command Line Arguments** (MEDIUM PRIORITY - User Request)
**Current**: Uses argparse with --crawl-id, --domain, etc.
**User Preference**: "I don't like using command line arguments. Please replace with a config file, one in Python that can be simply imported"
**Need**: Replace CLI args with importable Python config file

#### 5. **No Multi-Crawl Support** (HIGH PRIORITY)
**Current**: Single crawl_id (CC-MAIN-2020-16)
**Problem**: COVID spanned 3+ years, need multiple crawls
**Need**: Support for multiple crawl IDs in config

#### 6. **Limited Keyword Coverage** (MEDIUM PRIORITY)
**Current**: `covid,coronavirus,virus,lockdown,vaccine,quarantine`
**Missing**: 
- COVID variants: omicron, delta, alpha, beta, gamma
- NZ-specific: border, travel bubble, managed isolation
- Health terms: cases, deaths, hospitalization, ICU
- Policy terms: alert level, restrictions, curfew, mask mandate

#### 7. **No Deduplication** (LOW PRIORITY)
**Current**: SQLite UNIQUE on URL (good)
**Problem**: Same article might appear in multiple crawls with different URLs
**Need**: Content-based deduplication (hash of content)

#### 8. **No Export Functionality** (LOW PRIORITY)
**Current**: SQLite only
**Need**: Export to CSV/JSON for analysis

## Recommended Improvements (Priority Order)

### Phase 1: Essential for COVID Timeline (Must Have)

1. **Multi-source support**
   - Add config for multiple domain patterns
   - Support: Stuff, NZ Herald, RNZ, TVNZ, 3News, Newsroom

2. **Multi-crawl support**
   - Config for list of crawl IDs (CC-MAIN-2020-16 through CC-MAIN-2022-52)
   - Process multiple crawls sequentially

3. **Date range filtering**
   - Filter URLs by timestamp in CDX query
   - Config: start_date, end_date

4. **Publish date extraction**
   - Extract article publish date from HTML
   - Store in database separately from crawl timestamp

5. **Replace CLI with Python config**
   - Create `config/settings.py` as importable config
   - Remove argparse, use config file only

### Phase 2: Quality Improvements (Should Have)

6. **Expanded keyword list**
   - Add COVID variants, NZ-specific terms, health metrics

7. **Progress tracking**
   - Resume from checkpoint if interrupted
   - Track which WARC files processed

8. **Better article extraction**
   - Use readability-algorithm or newspaper3k
   - Extract author, publish date, tags

### Phase 3: Analysis Ready (Nice to Have)

9. **Export functionality**
   - Export to CSV for pandas analysis
   - Export to JSON

10. **Content deduplication**
    - Hash-based duplicate detection
    - Handle same article, different URL

11. **Salience metrics**
    - Calculate articles per day
    - Track keyword frequency over time
    - Generate timeline visualization

## Technical Debt

- No tests (should add basic unit tests)
- No pre-commit hooks
- No performance benchmarks
- No documentation on how to analyze results

## Recommendation

**Create a new branch** and implement:
1. Multi-source config (5-10 NZ news domains)
2. Multi-crawl support (2020-2022)
3. Python config file (replace CLI)
4. Date filtering
5. Publish date extraction

This will give you a proper COVID salience dataset.
