# PGSEM Electives Allocation System

[![CI](https://github.com/iimb-pgsem/electives/actions/workflows/ci.yml/badge.svg)](https://github.com/iimb-pgsem/electives/actions/workflows/ci.yml)
![Language](https://img.shields.io/github/languages/top/iimb-pgsem/electives)
[![License: MIT](https://img.shields.io/github/license/iimb-pgsem/electives)](LICENSE)
![Repo Size](https://img.shields.io/github/repo-size/iimb-pgsem/electives)
![Last Commit](https://img.shields.io/github/last-commit/iimb-pgsem/electives)
![GitHub Stars](https://img.shields.io/github/stars/iimb-pgsem/electives)

A course elective preference collection and allocation system built for
the Post-Graduate Program in Software Enterprise Management (PGSEM) at
the Indian Institute of Management, Bangalore (IIM-B).

Students submit prioritized course preferences through a web interface.
The allocation engine then assigns courses using a multi-factor ranking
algorithm that considers seniority, course priority, and CGPA.

**[Allocation Process and Rules](https://iimb-pgsem.github.io/electives/)** — the original instructions page explaining how the system works, with worked examples.

## History

This system was developed in 2006-2007 and used for quarterly elective
allocation cycles starting Q4 2005-06 and continuing for a few years.
The codebase is ~5,200 SLOC of Perl across 21 files. The original
version control was CVS; this repository was reconstructed from those
CVS archives in 2026 with proper commit history, conventional commit
messages, and PII removed.

## Authors

- **Sankaranarayanan Viswanathan** ([@kvsankar](https://github.com/kvsankar))
- **Abhay Ghaisas** ([@abhayghaisas](https://github.com/abhayghaisas))

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Web Interface                   │
│  electives.cgi  summary.cgi  feedback.cgi  ...  │
└──────────────────────┬──────────────────────────┘
                       │ CGI / DBI
              ┌────────┴────────┐
              │   MySQL (pgsem) │
              └────────┬────────┘
                       │ reads choices from DB / files
              ┌────────┴────────┐
              │    elec.pl      │  ← allocation engine
              │  (batch mode)   │
              └────────┬────────┘
                       │ reads
    ┌──────────┬───────┴───────┬──────────────┐
    │          │               │              │
courses.txt  students.txt  choices.txt  project_students.txt
```

### Components

| File | Purpose |
|------|---------|
| `elec.pl` | Core allocation engine — reads input files, runs the algorithm, writes results |
| `electives.cgi` | Main CGI web app — student login, preference submission, results display |
| `Elec.pm` | Shared module — data structures and loaders for courses, students, choices |
| `ElecConfig.pm` | Configuration module — reads `config.txt` key-value pairs |
| `ElecUtils.pm` | Utility functions — `err_print()`, `skip_line()` |
| `summary.cgi` | Admin summary of submitted preferences by course |
| `summarytext.cgi` | Plain-text variant of summary |
| `feedback.cgi` | Student feedback collection |
| `feedbackresults.cgi` | Display collected feedback |
| `p3results.cgi` | Phase 3 allocation results display |
| `passcode.cgi` | Generate and email login passcodes |
| `dblog.cgi` | Admin view of database log entries |
| `project.cgi` | Project assignment management |
| `graduation.cgi` | Convocation/graduation candidate management |
| `graduation-profiles.cgi` | Individual graduation profile display |
| `mailresults.pl` | Email allocation results to students |
| `sendmails.pl` | Bulk email sending utility |
| `sendphaseonemails.pl` | Phase 1 opening notification emails |
| `genstudents.pl` | Test data generator for student roll numbers |
| `parselog.pl` | Log file parser |
| `pgsem-schema.sql` | MySQL database schema (authcode, choices, changes, log) |

## Allocation Algorithm

The system uses a three-phase allocation process:

### Phase 1: Demand Collection
Students submit the number of courses they plan to take and a prioritized
list of preferences (non-binding). This data is used to schedule classes
and minimize conflicts.

### Phase 2: Allocation (2A + 2B)
Students submit binding preferences. The engine allocates courses based on:

1. **Seniority** (`older_and_lazy_rule`): Earlier batch students who haven't
   completed >=93 credits get priority. Students who missed Phase 1 or
   Phase 2A lose seniority.
2. **Course priority**: Within a seniority bucket, students who ranked a
   course higher get priority.
3. **CGPA**: Tie-breaker within the same seniority and priority level.
4. **Roll number**: Final tie-breaker (lower roll number wins).

A student gets a course unless:
- They've been allocated all courses they requested
- Their CGPA limits them (< 2.75 → max 3 courses; < 2.75 with project → max 2)
- A higher-priority course was already allocated in the same time slot
- The course reached its capacity cap

### Phase 3: Add/Drop/Swap
Students can request to add, drop, or swap courses subject to capacity
and schedule constraints.

### Sample allocation output

![Allocation spreadsheet](docs/images/allocation-internal.png)

*A snapshot of the allocation engine's Excel output showing per-course student rankings, priorities, and allocation status (student names masked).*

## Data Formats

All data files use semicolon-delimited fields. Lines starting with `#`
are comments; blank lines are skipped.

### courses.txt
```
# code; name; instructor; cap; slot; status; site; barred
CS101; Data Structures; Prof. Sharma; 60; 1; A; B;
FIN201; Corporate Finance; Prof. Rao; 50; 2; A; B+C;
```
- **status**: `A` (active), `D` (dropped), `N` (not available)
- **site**: `B` (Bangalore), `C` (Chennai), `B+C` (distributed)
- **barred**: year (e.g., `2005`) — batch barred from this course

### students.txt
```
# rollno; name; email; cgpa; credits; site
2004101; Student Name; student@example.com; 3.45; 72; B
```

### choices.txt
```
# rollno; ncourses; comma-separated-courses (priority order)
2004101; 3; CS101,FIN201,MKT301
```
Note: the course list is **comma-separated** within the third semicolon-delimited field.

### project_students.txt
```
# one roll number per line
2004105
2004110
```

### config.txt
```
phase=2
adminpassword=changeme
datasource=DBI:mysql:database=pgsem;host=localhost
dblogin=pgsem
dbpassword=changeme
quarter_str=2006-07 Quarter 2 (September - November 2006)
quarter_starts_str=Sep. 2006
send_email=0
pop_required=0
deadline=2006-08-20
moodle_url=http://localhost/moodle
max_cgpa=4.0
min_cgpa_four_courses=2.75
min_credits=0
credits_pass=93
current_year=2004
max_courses=4
default_cap=65
default_mincap=15
default_status=A
default_site=B
default_cgpa=4.0
give_priority_to_seniors=1
give_priority_to_cgpa=1
```

## Running the Allocation Engine

### Prerequisites
- Perl 5.x with modules: `DBI`, `Spreadsheet::WriteExcel`, `POSIX`
- MySQL (for the web interface; not required for batch allocation)

### Batch allocation (no database required)

```bash
cd test/
PERL5LIB=.. perl ../elec.pl
```

This reads from the current directory:
- `config.txt` — allocation parameters
- `courses-internal.txt` — course catalog (internal format with single-site rows)
- `students.txt` — student roster
- `choices.txt` — submitted preferences
- `project-students.txt` — students doing projects
- `choices-p1.txt` — Phase 1 participant roll numbers
- `p2a-students.txt`, `p2-students.txt` — Phase 2 participant lists

Output goes to stdout and `allocation-internal.txt`. An Excel workbook
(`allocation.xls`) is also generated if `Spreadsheet::WriteExcel` is
installed.

### Web interface

1. Create the MySQL database: `mysql < pgsem-schema.sql`
2. Configure `config.txt` with database credentials
3. Deploy CGI scripts to a web server with CGI support
4. Access `electives.cgi` through the browser

## Testing

The project includes a CI pipeline ([GitHub Actions](.github/workflows/ci.yml))
and a complete set of synthetic test fixtures in `test/`.

### Test fixtures

The `test/` directory contains everything needed to run the allocation
engine without a database: 10 courses, 21 synthetic students across
3 batches (2003–2005), and realistic preference data. The data is
designed to exercise:

- **Seniority ranking**: 2003 batch students are allocated before 2004,
  then 2005
- **Seniority loss**: student 2003106 has >=93 credits and loses
  seniority privilege
- **Schedule conflict detection**: courses sharing the same time slot
  cannot both be allocated to one student
- **CGPA-based tie-breaking**: within the same seniority and priority
- **Project student handling**: project students get one fewer elective
  slot

### CI pipeline

On every push and pull request, CI runs three checks:

1. **Syntax check** — `perl -c` on all `.pl`, `.pm`, and `.cgi` files
2. **Allocation test** — runs the engine against test fixtures and
   verifies allotments, course/student output sections, seniority
   ordering, schedule conflict detection, and Excel workbook generation
3. **PII scan** — ensures no student email addresses or data files are
   present in the repository

## Repository Structure

```
.
├── Elec.pm                     # Core data module
├── ElecConfig.pm               # Configuration reader
├── ElecUtils.pm                # Utility functions
├── elec.pl                     # Allocation engine (batch)
├── electives.cgi               # Web interface (CGI)
├── pgsem-schema.sql            # Database schema
├── test/                       # Test fixtures (synthetic data, no PII)
│   ├── config.txt              # Sample configuration
│   ├── courses.txt             # Sample courses (display format)
│   ├── courses-internal.txt    # Sample courses (allocation format)
│   ├── students.txt            # 21 synthetic students across 3 batches
│   ├── choices.txt             # Synthetic preferences
│   ├── choices-p1.txt          # Phase 1 participant list
│   ├── p2a-students.txt        # Phase 2A participant list
│   ├── p2-students.txt         # Phase 2 participant list
│   └── project-students.txt    # Students doing projects
├── docs/                       # GitHub Pages site
│   ├── index.html
│   └── electives-allocation.html
├── sankara.net/                # Original project website (archived)
│   ├── electives-allocation.html
│   └── pgsem/
└── [other CGI scripts and utilities]
```

## Documentation

The original allocation rules and instructions page is hosted via
GitHub Pages at https://iimb-pgsem.github.io/electives/

## Branches

- **main**: Full CVS history (Jan 2006 – Mar 2007), 132 commits
- **deployment-fork**: Fork from Aug 2006 adapted for Linux web hosting,
  adds `ConfigDir.pm`, `images.cgi`, `.htaccess`

## Credits

This work was supported by [Professor Rajendra K Bandi](https://digest.iimb.ac.in/2025/07/professor-rajendra-k-bandi/),
ex PGSEM Chairperson at IIM Bangalore
([LinkedIn](https://www.linkedin.com/in/rajendra-bandi-a8bb4/),
[Chanakya University](https://chanakyauniversity.edu.in/faculties/dr-rajendra-bandi/)).

## License

[MIT](LICENSE) — Copyright (c) 2006-2007 Sankaranarayanan Viswanathan and Abhay Ghaisas.
