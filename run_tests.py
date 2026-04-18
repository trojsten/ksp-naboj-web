#!/usr/bin/env python
import os
import django
import sys
import importlib
import unittest

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ksp-naboj.settings')
django.setup()

# Import test modules
comp_tests = importlib.import_module('ksp-naboj.competition.tests')
team_tests = importlib.import_module('ksp-naboj.team.tests')
problem_tests = importlib.import_module('ksp-naboj.problem.tests')
submission_tests = importlib.import_module('ksp-naboj.submission.tests')
services_tests = importlib.import_module('ksp-naboj.team.tests_services')

# Create test suites
comp_suite = unittest.TestLoader().loadTestsFromModule(comp_tests)
team_suite = unittest.TestLoader().loadTestsFromModule(team_tests)
problem_suite = unittest.TestLoader().loadTestsFromModule(problem_tests)
submission_suite = unittest.TestLoader().loadTestsFromModule(submission_tests)
services_suite = unittest.TestLoader().loadTestsFromModule(services_tests)

# Combine all suites
all_tests = unittest.TestSuite([comp_suite, team_suite, problem_suite, submission_suite, services_suite])

# Run tests
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(all_tests)

# Exit with appropriate code
sys.exit(0 if result.wasSuccessful() else 1)
