# KSP-Naboj-Vibe

A web-based programming competition platform inspired by the Náboj math competition, where teams of 4 students collaborate to solve programming problems within 2 hours.

## Project Overview

Náboj is an international mathematical competition designed for teams of high-school students. This project adapts the concept to programming competitions, maintaining the core principles:
- Teams of 4-5 students from the same school
- 2-hour time limit
- Progressive problem unlock (start with 6 problems, get new ones as you solve them)
- Real-time collaboration and coordination
- Focus on teamwork and problem-solving skills

## Technical Stack

- **Backend**: Django with Trojsten's django-scaffold
- **Database**: PostgreSQL with psycopg3 + binary
- **Frontend**: TailwindCSS + htmx + Stimulus
- **Authentication**: OIDC (mozilla-django-oidc) for Trojsten ID
- **Judge Integration**: Trojsten's judge-client
- **Code Editor**: Monaco Editor
- **Deployment**: Docker (trojsten/django-docker), gunicorn

## Project Structure

Following Trojsten convention with all apps inside the project folder:

```
ksp-naboj-vibe/
├── CLAUDE.md
├── requirements.txt
├── manage.py
├── naboj/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   ├── urls.py
│   ├── wsgi.py
│   └── apps/
│       ├── competition/
│       │   ├── __init__.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── views.py
│       │   ├── urls.py
│       │   ├── forms.py
│       │   ├── services.py
│       │   └── templates/
│       ├── teams/
│       └── problems/
└── templates/
    ├── base.html
    └── partials/
```

## Core Features

### Competition Flow
- **Timer**: 2-hour competition countdown
- **Progressive Unlock**: Start with 6 problems, unlock new ones as you solve them
- **Real-time Updates**: Live team coordination and score tracking
- **Team Collaboration**: See what teammates are working on and submission history

### Problem Management
- **Problem Listing**: Browse available problems with descriptions
- **Integrated Editor**: Monaco Editor for writing code
- **Multiple Languages**: Support for all judge-client languages
- **Sample I/O**: Display sample input/output for each problem

### Team Features
- **Team Dashboard**: Overview of team progress and member activity
- **Submission History**: View all team submissions and results
- **Problem Status**: See which problems each team member is working on
- **Scoreboard**: Team-specific and overall competition rankings

## Implementation Phases

### Phase 1: Setup and Basic Structure
- [x] Create project documentation
- [ ] Initialize Django project using django-scaffold
- [ ] Set up app structure following Trojsten convention
- [ ] Create basic models (Team, Problem, Submission)
- [ ] Set up templates and static files

### Phase 2: Core Features
- [ ] Problem viewing interface
- [ ] Integrated code editor (Monaco Editor)
- [ ] Mock submission system (simulated results)
- [ ] Team coordination features
- [ ] Progressive problem unlock system
- [ ] Competition timer and scoreboard

### Phase 3: Authentication Integration
- [ ] Configure OIDC with mozilla-django-oidc
- [ ] Set up Trojsten ID integration
- [ ] Update user management for OIDC
- [ ] Migrate existing data to use OIDC user IDs

### Phase 4: Judge Integration
- [ ] Integrate with Trojsten's judge-client
- [ ] Replace mock submission system
- [ ] Implement real-time result polling
- [ ] Add error handling for judge communication

### Phase 5: Polish and Testing
- [ ] UI/UX improvements
- [ ] Stress testing with multiple teams
- [ ] Documentation and deployment setup

## Design Patterns

Following django-scaffold recommendations:

### Fat Models, Thin Views
- Business logic should be in models or service layer
- Views handle input/output processing and delegation
- Models should encapsulate domain logic and data integrity

### Custom Managers and QuerySets
- **Manager**: Table-level operations on multiple instances
- **QuerySet**: Filtering, annotations, ordering operations

### Service Layer
For complex application logic involving:
- Multiple models
- External service calls
- Complex business workflows

## Development Setup

```bash
# Initialize project using django-scaffold
uvx copier copy https://github.com/trojsten/django-scaffold.git .

# Install dependencies
uv sync
pnpm install

# Create apps following Trojsten structure
mkdir naboj/apps/competition
./manage.py startapp competition naboj/apps/competition
```

## Key Models

### Team
- Name, school, members
- Competition category (Junior/Senior)
- Current problems and progress tracking

### Problem
- Title, description, difficulty
- Sample input/output
- Unlock order and dependencies
- Test cases (for judge integration)

### Submission
- Team, problem, code, language
- Result status and timestamp
- Execution details (when integrated with judge)

### User
- Team member information
- OIDC integration
- Permissions and roles

## Frontend Technologies

- **TailwindCSS**: Utility-first CSS framework
- **htmx**: AJAX-style interactions without writing JavaScript
- **Stimulus**: JavaScript framework for interactive components
- **Monaco Editor**: VS Code editor in the browser

## Development Tools

- **ruff**: Python code formatting
- **djade**: Django template formatting
- **pre-commit**: Automatic code quality checks
- **django-debug-toolbar**: Development debugging
- **sentry-sdk**: Error reporting and monitoring

## Competition Rules (Adapted from Náboj Math)

1. **Teams**: 4-5 members from the same school
2. **Duration**: 2 hours
3. **Problems**: Start with 6, unlock new ones as you solve them
4. **Collaboration**: Only within team members
5. **Resources**: No external resources or communication
6. **Winning**: Most problems solved, tie-breaking by problem difficulty and time

## Future Enhancements

- Practice mode with past competitions
- Problem authoring interface
- Advanced analytics and statistics
- Mobile-responsive design
- Real-time competition streaming
- Integration with popular IDEs