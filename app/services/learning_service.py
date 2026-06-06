from app.db.firestore import FirestoreService
from typing import Dict, List, Optional
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Role-specific documentation mapping
# Each role has its own curated set of documentation for every skill in its
# roadmap.  When a skill appears in multiple roles (e.g. "python" in both
# backend-dev and data-scientist) each role gets resources appropriate to its
# context and depth.
# ──────────────────────────────────────────────────────────────────────────────

ROLE_SPECIFIC_DOCS = {
    # ── Frontend Developer ──────────────────────────────────────────────────
    'frontend-dev': {
        'html': [
            {'title': 'MDN Web Docs: HTML', 'url': 'https://developer.mozilla.org/en-US/docs/Web/HTML', 'provider': 'Mozilla MDN'},
            {'title': 'HTML Living Standard', 'url': 'https://html.spec.whatwg.org/', 'provider': 'WHATWG'},
            {'title': 'Web Accessibility (WAI-ARIA)', 'url': 'https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA', 'provider': 'Mozilla MDN'}
        ],
        'css': [
            {'title': 'MDN Web Docs: CSS', 'url': 'https://developer.mozilla.org/en-US/docs/Web/CSS', 'provider': 'Mozilla MDN'},
            {'title': 'CSS-Tricks Complete Guide to Flexbox', 'url': 'https://css-tricks.com/snippets/css/a-guide-to-flexbox/', 'provider': 'CSS-Tricks'},
            {'title': 'CSS Grid Layout Guide', 'url': 'https://css-tricks.com/snippets/css/complete-guide-grid/', 'provider': 'CSS-Tricks'}
        ],
        'js': [
            {'title': 'MDN JavaScript Guide', 'url': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide', 'provider': 'Mozilla MDN'},
            {'title': 'Modern JavaScript Tutorial', 'url': 'https://javascript.info/', 'provider': 'Javascript.info'},
            {'title': 'DOM Manipulation Guide', 'url': 'https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Client-side_web_APIs/Manipulating_documents', 'provider': 'Mozilla MDN'}
        ],
        'ts': [
            {'title': 'TypeScript Handbook', 'url': 'https://www.typescriptlang.org/docs/handbook/', 'provider': 'Microsoft'},
            {'title': 'TypeScript in React', 'url': 'https://react.dev/learn/typescript', 'provider': 'Meta'}
        ],
        'react': [
            {'title': 'React Official Documentation', 'url': 'https://react.dev/reference/react', 'provider': 'Meta'},
            {'title': 'React Learn: Quick Start', 'url': 'https://react.dev/learn', 'provider': 'Meta'},
            {'title': 'React Hooks Reference', 'url': 'https://react.dev/reference/react/hooks', 'provider': 'Meta'}
        ],
        'redux': [
            {'title': 'Redux Toolkit Documentation', 'url': 'https://redux-toolkit.js.org/introduction/getting-started', 'provider': 'Redux'},
            {'title': 'Redux Essentials Tutorial', 'url': 'https://redux.js.org/tutorials/essentials/part-1-overview-concepts', 'provider': 'Redux'}
        ],
        'git': [
            {'title': 'Git for Frontend Developers', 'url': 'https://www.atlassian.com/git/tutorials', 'provider': 'Atlassian'},
            {'title': 'Pro Git Book', 'url': 'https://git-scm.com/book/en/v2', 'provider': 'Scott Chacon & Ben Straub'}
        ],
        'webpack': [
            {'title': 'Webpack Getting Started', 'url': 'https://webpack.js.org/guides/getting-started/', 'provider': 'Webpack'},
            {'title': 'Vite Documentation', 'url': 'https://vitejs.dev/guide/', 'provider': 'Vite'}
        ],
        'tailwind': [
            {'title': 'Tailwind CSS Documentation', 'url': 'https://tailwindcss.com/docs', 'provider': 'Tailwind Labs'},
            {'title': 'Tailwind CSS Component Examples', 'url': 'https://tailwindui.com/components', 'provider': 'Tailwind Labs'}
        ]
    },

    # ── Backend Developer ───────────────────────────────────────────────────
    'backend-dev': {
        'python': [
            {'title': 'Python 3 Official Tutorial', 'url': 'https://docs.python.org/3/tutorial/', 'provider': 'Python.org'},
            {'title': 'Real Python: Backend Development', 'url': 'https://realpython.com/tutorials/web-dev/', 'provider': 'Real Python'},
            {'title': 'Python Design Patterns', 'url': 'https://refactoring.guru/design-patterns/python', 'provider': 'Refactoring Guru'}
        ],
        'sql': [
            {'title': 'PostgreSQL Official Documentation', 'url': 'https://www.postgresql.org/docs/', 'provider': 'PostgreSQL'},
            {'title': 'SQL for Backend Developers', 'url': 'https://www.w3schools.com/sql/', 'provider': 'W3Schools'},
            {'title': 'Database Design & Normalization', 'url': 'https://www.guru99.com/database-normalization.html', 'provider': 'Guru99'}
        ],
        'flask': [
            {'title': 'Flask Official Documentation', 'url': 'https://flask.palletsprojects.com/', 'provider': 'Pallets Project'},
            {'title': 'Flask Mega-Tutorial', 'url': 'https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world', 'provider': 'Miguel Grinberg'}
        ],
        'django': [
            {'title': 'Django Official Documentation', 'url': 'https://docs.djangoproject.com/', 'provider': 'Django Project'},
            {'title': 'Django REST Framework', 'url': 'https://www.django-rest-framework.org/', 'provider': 'DRF'}
        ],
        'postgresql': [
            {'title': 'PostgreSQL Documentation', 'url': 'https://www.postgresql.org/docs/', 'provider': 'PostgreSQL'},
            {'title': 'PostgreSQL Tutorial', 'url': 'https://www.postgresqltutorial.com/', 'provider': 'PostgreSQL Tutorial'}
        ],
        'rest-api': [
            {'title': 'RESTful API Design Guide', 'url': 'https://restfulapi.net/', 'provider': 'RESTful API'},
            {'title': 'API Design Best Practices', 'url': 'https://swagger.io/resources/articles/best-practices-in-api-design/', 'provider': 'Swagger'}
        ],
        'git': [
            {'title': 'Git Branching Strategies for Teams', 'url': 'https://www.atlassian.com/git/tutorials/comparing-workflows', 'provider': 'Atlassian'},
            {'title': 'Pro Git Book', 'url': 'https://git-scm.com/book/en/v2', 'provider': 'Scott Chacon & Ben Straub'}
        ],
        'docker': [
            {'title': 'Docker for Backend Development', 'url': 'https://docs.docker.com/get-started/', 'provider': 'Docker Inc.'},
            {'title': 'Dockerize Python Applications', 'url': 'https://docs.docker.com/language/python/', 'provider': 'Docker Inc.'}
        ],
        'nodejs': [
            {'title': 'Node.js Documentation', 'url': 'https://nodejs.org/en/docs/', 'provider': 'Node.js'},
            {'title': 'Express.js Guide', 'url': 'https://expressjs.com/en/guide/routing.html', 'provider': 'Express.js'}
        ]
    },

    # ── Full Stack Developer ────────────────────────────────────────────────
    'fullstack-dev': {
        'html': [
            {'title': 'MDN Web Docs: HTML', 'url': 'https://developer.mozilla.org/en-US/docs/Web/HTML', 'provider': 'Mozilla MDN'},
            {'title': 'Semantic HTML for Full Stack Devs', 'url': 'https://web.dev/learn/html', 'provider': 'Google web.dev'}
        ],
        'css': [
            {'title': 'MDN Web Docs: CSS', 'url': 'https://developer.mozilla.org/en-US/docs/Web/CSS', 'provider': 'Mozilla MDN'},
            {'title': 'Modern CSS Solutions', 'url': 'https://moderncss.dev/', 'provider': 'Stephanie Eckles'}
        ],
        'js': [
            {'title': 'JavaScript for Full Stack Developers', 'url': 'https://javascript.info/', 'provider': 'Javascript.info'},
            {'title': 'Full Stack Open – JavaScript', 'url': 'https://fullstackopen.com/en/part1', 'provider': 'University of Helsinki'}
        ],
        'python': [
            {'title': 'Python Official Documentation', 'url': 'https://docs.python.org/3/', 'provider': 'Python.org'},
            {'title': 'Full Stack Python', 'url': 'https://www.fullstackpython.com/', 'provider': 'Full Stack Python'}
        ],
        'nodejs': [
            {'title': 'Node.js Documentation', 'url': 'https://nodejs.org/en/docs/', 'provider': 'Node.js'},
            {'title': 'Full Stack Open – Node', 'url': 'https://fullstackopen.com/en/part3', 'provider': 'University of Helsinki'}
        ],
        'sql': [
            {'title': 'SQL Tutorial', 'url': 'https://www.w3schools.com/sql/', 'provider': 'W3Schools'},
            {'title': 'Full Stack Database Design', 'url': 'https://www.postgresqltutorial.com/', 'provider': 'PostgreSQL Tutorial'}
        ],
        'rest-api': [
            {'title': 'RESTful API Best Practices', 'url': 'https://restfulapi.net/', 'provider': 'RESTful API'},
            {'title': 'GraphQL vs REST', 'url': 'https://graphql.org/learn/', 'provider': 'GraphQL Foundation'}
        ],
        'react': [
            {'title': 'React Official Docs', 'url': 'https://react.dev/learn', 'provider': 'Meta'},
            {'title': 'Full Stack Open – React', 'url': 'https://fullstackopen.com/en/part1', 'provider': 'University of Helsinki'}
        ],
        'git': [
            {'title': 'Git & GitHub for Full Stack Devs', 'url': 'https://www.atlassian.com/git/tutorials', 'provider': 'Atlassian'},
            {'title': 'Git Reference Manual', 'url': 'https://git-scm.com/doc', 'provider': 'Git Core'}
        ],
        'ts': [
            {'title': 'TypeScript Documentation', 'url': 'https://www.typescriptlang.org/docs/', 'provider': 'Microsoft'},
            {'title': 'TypeScript Deep Dive', 'url': 'https://basarat.gitbook.io/typescript/', 'provider': 'Basarat Ali'}
        ],
        'postgresql': [
            {'title': 'PostgreSQL Documentation', 'url': 'https://www.postgresql.org/docs/', 'provider': 'PostgreSQL'},
            {'title': 'PostgreSQL Tutorial', 'url': 'https://www.postgresqltutorial.com/', 'provider': 'PostgreSQL Tutorial'}
        ]
    },

    # ── Data Scientist ──────────────────────────────────────────────────────
    'data-scientist': {
        'python': [
            {'title': 'Python for Data Science Handbook', 'url': 'https://jakevdp.github.io/PythonDataScienceHandbook/', 'provider': 'Jake VanderPlas'},
            {'title': 'Kaggle: Python Course', 'url': 'https://www.kaggle.com/learn/python', 'provider': 'Kaggle'},
            {'title': 'Real Python: Data Science', 'url': 'https://realpython.com/tutorials/data-science/', 'provider': 'Real Python'}
        ],
        'sql': [
            {'title': 'Kaggle: SQL Course', 'url': 'https://www.kaggle.com/learn/intro-to-sql', 'provider': 'Kaggle'},
            {'title': 'SQL for Data Scientists', 'url': 'https://mode.com/sql-tutorial/', 'provider': 'Mode Analytics'}
        ],
        'pandas': [
            {'title': 'Pandas Official Documentation', 'url': 'https://pandas.pydata.org/docs/', 'provider': 'Pandas'},
            {'title': 'Kaggle: Pandas Course', 'url': 'https://www.kaggle.com/learn/pandas', 'provider': 'Kaggle'},
            {'title': '10 Minutes to Pandas', 'url': 'https://pandas.pydata.org/docs/user_guide/10min.html', 'provider': 'Pandas'}
        ],
        'numpy': [
            {'title': 'NumPy Official Documentation', 'url': 'https://numpy.org/doc/stable/', 'provider': 'NumPy'},
            {'title': 'NumPy Quickstart Tutorial', 'url': 'https://numpy.org/doc/stable/user/quickstart.html', 'provider': 'NumPy'}
        ],
        'scikit-learn': [
            {'title': 'Scikit-learn Official Tutorials', 'url': 'https://scikit-learn.org/stable/tutorial/index.html', 'provider': 'Scikit-learn'},
            {'title': 'Kaggle: Intro to ML', 'url': 'https://www.kaggle.com/learn/intro-to-machine-learning', 'provider': 'Kaggle'}
        ],
        'tensorflow': [
            {'title': 'TensorFlow Tutorials', 'url': 'https://www.tensorflow.org/tutorials', 'provider': 'TensorFlow'},
            {'title': 'Keras Documentation', 'url': 'https://keras.io/guides/', 'provider': 'Keras'}
        ],
        'matplotlib': [
            {'title': 'Matplotlib Tutorials', 'url': 'https://matplotlib.org/stable/tutorials/index.html', 'provider': 'Matplotlib'},
            {'title': 'Data Visualization with Python', 'url': 'https://seaborn.pydata.org/tutorial.html', 'provider': 'Seaborn'}
        ],
        'tableau': [
            {'title': 'Tableau Public Training', 'url': 'https://public.tableau.com/app/resources/learn', 'provider': 'Tableau'},
            {'title': 'Tableau Learning Resources', 'url': 'https://www.tableau.com/learn/training', 'provider': 'Tableau'}
        ]
    },

    # ── DevOps Engineer ─────────────────────────────────────────────────────
    'devops-engineer': {
        'linux': [
            {'title': 'Linux Documentation Project', 'url': 'https://tldp.org/', 'provider': 'TLDP'},
            {'title': 'Linux Command Line Basics', 'url': 'https://linuxjourney.com/', 'provider': 'Linux Journey'},
            {'title': 'RHEL System Administration', 'url': 'https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/', 'provider': 'Red Hat'}
        ],
        'bash': [
            {'title': 'Bash Reference Manual', 'url': 'https://www.gnu.org/software/bash/manual/', 'provider': 'GNU'},
            {'title': 'Advanced Bash-Scripting Guide', 'url': 'https://tldp.org/LDP/abs/html/', 'provider': 'TLDP'}
        ],
        'docker': [
            {'title': 'Docker Documentation', 'url': 'https://docs.docker.com/', 'provider': 'Docker Inc.'},
            {'title': 'Docker Compose Guide', 'url': 'https://docs.docker.com/compose/', 'provider': 'Docker Inc.'},
            {'title': 'Docker Security Best Practices', 'url': 'https://docs.docker.com/engine/security/', 'provider': 'Docker Inc.'}
        ],
        'kubernetes': [
            {'title': 'Kubernetes Official Documentation', 'url': 'https://kubernetes.io/docs/home/', 'provider': 'CNCF'},
            {'title': 'Kubernetes the Hard Way', 'url': 'https://github.com/kelseyhightower/kubernetes-the-hard-way', 'provider': 'Kelsey Hightower'},
            {'title': 'Kubernetes Patterns', 'url': 'https://kubernetes.io/docs/concepts/workloads/', 'provider': 'CNCF'}
        ],
        'aws': [
            {'title': 'AWS DevOps Documentation', 'url': 'https://docs.aws.amazon.com/devops/', 'provider': 'AWS'},
            {'title': 'AWS Well-Architected Framework', 'url': 'https://aws.amazon.com/architecture/well-architected/', 'provider': 'AWS'}
        ],
        'terraform': [
            {'title': 'Terraform Documentation', 'url': 'https://developer.hashicorp.com/terraform/docs', 'provider': 'HashiCorp'},
            {'title': 'Learn Terraform', 'url': 'https://developer.hashicorp.com/terraform/tutorials', 'provider': 'HashiCorp'}
        ],
        'jenkins': [
            {'title': 'Jenkins Documentation', 'url': 'https://www.jenkins.io/doc/', 'provider': 'Jenkins'},
            {'title': 'Jenkins Pipeline Syntax', 'url': 'https://www.jenkins.io/doc/book/pipeline/syntax/', 'provider': 'Jenkins'}
        ],
        'prometheus': [
            {'title': 'Prometheus Documentation', 'url': 'https://prometheus.io/docs/introduction/overview/', 'provider': 'Prometheus'},
            {'title': 'Grafana + Prometheus Guide', 'url': 'https://grafana.com/docs/grafana/latest/datasources/prometheus/', 'provider': 'Grafana Labs'}
        ]
    },

    # ── ML Engineer ─────────────────────────────────────────────────────────
    'ml-engineer': {
        'python': [
            {'title': 'Python for ML Engineers', 'url': 'https://scikit-learn.org/stable/tutorial/index.html', 'provider': 'Scikit-learn'},
            {'title': 'Kaggle: Python for Data Science', 'url': 'https://www.kaggle.com/learn/python', 'provider': 'Kaggle'},
            {'title': 'Advanced Python Patterns for ML', 'url': 'https://realpython.com/tutorials/machine-learning/', 'provider': 'Real Python'}
        ],
        'statistics': [
            {'title': 'Khan Academy: Statistics', 'url': 'https://www.khanacademy.org/math/statistics-probability', 'provider': 'Khan Academy'},
            {'title': 'Think Stats (Free Book)', 'url': 'https://greenteapress.com/thinkstats2/html/index.html', 'provider': 'Allen B. Downey'}
        ],
        'scikit-learn': [
            {'title': 'Scikit-learn User Guide', 'url': 'https://scikit-learn.org/stable/user_guide.html', 'provider': 'Scikit-learn'},
            {'title': 'ML with Scikit-learn – Kaggle', 'url': 'https://www.kaggle.com/learn/intermediate-machine-learning', 'provider': 'Kaggle'}
        ],
        'pandas': [
            {'title': 'Pandas for ML Feature Engineering', 'url': 'https://pandas.pydata.org/docs/', 'provider': 'Pandas'},
            {'title': 'Kaggle: Feature Engineering', 'url': 'https://www.kaggle.com/learn/feature-engineering', 'provider': 'Kaggle'}
        ],
        'tensorflow': [
            {'title': 'TensorFlow Developer Documentation', 'url': 'https://www.tensorflow.org/learn', 'provider': 'TensorFlow'},
            {'title': 'TensorFlow Model Garden', 'url': 'https://github.com/tensorflow/models', 'provider': 'TensorFlow'},
            {'title': 'TensorFlow Certification Guide', 'url': 'https://www.tensorflow.org/certificate', 'provider': 'TensorFlow'}
        ],
        'pytorch': [
            {'title': 'PyTorch Official Tutorials', 'url': 'https://pytorch.org/tutorials/', 'provider': 'PyTorch'},
            {'title': 'Deep Learning with PyTorch', 'url': 'https://pytorch.org/deep-learning-with-pytorch', 'provider': 'PyTorch'}
        ],
        'mlflow': [
            {'title': 'MLflow Documentation', 'url': 'https://mlflow.org/docs/latest/index.html', 'provider': 'MLflow'},
            {'title': 'MLOps Guide', 'url': 'https://ml-ops.org/', 'provider': 'ML-Ops Community'}
        ],
        'docker': [
            {'title': 'Docker for ML Deployment', 'url': 'https://docs.docker.com/get-started/', 'provider': 'Docker Inc.'},
            {'title': 'Containerizing ML Pipelines', 'url': 'https://docs.docker.com/language/python/', 'provider': 'Docker Inc.'}
        ]
    },

    # ── Cloud Architect ─────────────────────────────────────────────────────
    'cloud-architect': {
        'aws': [
            {'title': 'AWS Solutions Architect – Learning Path', 'url': 'https://aws.amazon.com/certification/certified-solutions-architect-associate/', 'provider': 'AWS'},
            {'title': 'AWS Well-Architected Framework', 'url': 'https://aws.amazon.com/architecture/well-architected/', 'provider': 'AWS'},
            {'title': 'AWS Architecture Center', 'url': 'https://aws.amazon.com/architecture/', 'provider': 'AWS'}
        ],
        'azure': [
            {'title': 'Microsoft Azure Documentation', 'url': 'https://learn.microsoft.com/en-us/azure/', 'provider': 'Microsoft'},
            {'title': 'Azure Architecture Center', 'url': 'https://learn.microsoft.com/en-us/azure/architecture/', 'provider': 'Microsoft'}
        ],
        'terraform': [
            {'title': 'Terraform Associate Certification', 'url': 'https://developer.hashicorp.com/terraform/tutorials/certification', 'provider': 'HashiCorp'},
            {'title': 'Advanced Terraform Patterns', 'url': 'https://developer.hashicorp.com/terraform/tutorials', 'provider': 'HashiCorp'}
        ],
        'cloudformation': [
            {'title': 'AWS CloudFormation Documentation', 'url': 'https://docs.aws.amazon.com/cloudformation/', 'provider': 'AWS'},
            {'title': 'CloudFormation Best Practices', 'url': 'https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html', 'provider': 'AWS'}
        ],
        'cloud-security': [
            {'title': 'AWS Security Documentation', 'url': 'https://docs.aws.amazon.com/security/', 'provider': 'AWS'},
            {'title': 'Cloud Security Alliance Guide', 'url': 'https://cloudsecurityalliance.org/research/guidance', 'provider': 'CSA'}
        ],
        'iam': [
            {'title': 'AWS IAM Documentation', 'url': 'https://docs.aws.amazon.com/IAM/latest/UserGuide/', 'provider': 'AWS'},
            {'title': 'Zero Trust Architecture (NIST)', 'url': 'https://csrc.nist.gov/publications/detail/sp/800-207/final', 'provider': 'NIST'}
        ],
        'microservices': [
            {'title': 'Microservices.io', 'url': 'https://microservices.io/', 'provider': 'Chris Richardson'},
            {'title': 'Building Microservices (Martin Fowler)', 'url': 'https://martinfowler.com/articles/microservices.html', 'provider': 'Martin Fowler'}
        ],
        'system-design': [
            {'title': 'System Design Primer', 'url': 'https://github.com/donnemartin/system-design-primer', 'provider': 'Donne Martin'},
            {'title': 'Cloud Design Patterns', 'url': 'https://learn.microsoft.com/en-us/azure/architecture/patterns/', 'provider': 'Microsoft'}
        ]
    },

    # ── Tech Lead ───────────────────────────────────────────────────────────
    'tech-lead': {
        'system-design': [
            {'title': 'System Design Primer', 'url': 'https://github.com/donnemartin/system-design-primer', 'provider': 'Donne Martin'},
            {'title': 'Grokking System Design', 'url': 'https://www.designgurus.io/course/grokking-the-system-design-interview', 'provider': 'Design Gurus'}
        ],
        'design-patterns': [
            {'title': 'Refactoring Guru – Design Patterns', 'url': 'https://refactoring.guru/design-patterns', 'provider': 'Refactoring Guru'},
            {'title': 'Source Making – Patterns', 'url': 'https://sourcemaking.com/design_patterns', 'provider': 'Source Making'}
        ],
        'team-leadership': [
            {'title': 'Engineering Manager Resources', 'url': 'https://github.com/charlax/engineering-management', 'provider': 'Community'},
            {'title': 'Staff Engineer Guide', 'url': 'https://staffeng.com/', 'provider': 'Will Larson'}
        ],
        'communication': [
            {'title': 'Technical Writing (Google)', 'url': 'https://developers.google.com/tech-writing', 'provider': 'Google'},
            {'title': 'Architecture Decision Records', 'url': 'https://adr.github.io/', 'provider': 'ADR Community'}
        ],
        'agile': [
            {'title': 'Agile Manifesto & Principles', 'url': 'https://agilemanifesto.org/', 'provider': 'Agile Alliance'},
            {'title': 'Scrum Guide', 'url': 'https://scrumguides.org/', 'provider': 'Scrum.org'}
        ],
        'project-management': [
            {'title': 'Atlassian Agile Coach', 'url': 'https://www.atlassian.com/agile', 'provider': 'Atlassian'},
            {'title': 'Project Management for Developers', 'url': 'https://www.pmi.org/learning/library', 'provider': 'PMI'}
        ],
        'architecture': [
            {'title': 'Martin Fowler – Software Architecture', 'url': 'https://martinfowler.com/architecture/', 'provider': 'Martin Fowler'},
            {'title': 'The Twelve-Factor App', 'url': 'https://12factor.net/', 'provider': '12 Factor'}
        ],
        'code-review': [
            {'title': 'Google Code Review Guidelines', 'url': 'https://google.github.io/eng-practices/review/', 'provider': 'Google'},
            {'title': 'Effective Code Reviews', 'url': 'https://github.com/google/eng-practices', 'provider': 'Google'}
        ]
    }
}

# Flat fallback mapping used when role is unknown or skill isn't listed for a role
GENERIC_DOCS_FALLBACK = {
    'html': [
        {'title': 'MDN Web Docs: HTML', 'url': 'https://developer.mozilla.org/en-US/docs/Web/HTML', 'provider': 'Mozilla MDN'}
    ],
    'css': [
        {'title': 'MDN Web Docs: CSS', 'url': 'https://developer.mozilla.org/en-US/docs/Web/CSS', 'provider': 'Mozilla MDN'}
    ],
    'javascript': [
        {'title': 'MDN JavaScript Guide', 'url': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide', 'provider': 'Mozilla MDN'}
    ],
    'js': [
        {'title': 'Modern JavaScript Tutorial', 'url': 'https://javascript.info/', 'provider': 'Javascript.info'}
    ],
    'typescript': [
        {'title': 'TypeScript Documentation', 'url': 'https://www.typescriptlang.org/docs/', 'provider': 'Microsoft'}
    ],
    'ts': [
        {'title': 'TypeScript Documentation', 'url': 'https://www.typescriptlang.org/docs/', 'provider': 'Microsoft'}
    ],
    'react': [
        {'title': 'React Documentation', 'url': 'https://react.dev/learn', 'provider': 'Meta'}
    ],
    'python': [
        {'title': 'Python 3 Documentation', 'url': 'https://docs.python.org/3/', 'provider': 'Python Software Foundation'}
    ],
    'sql': [
        {'title': 'W3Schools SQL Tutorial', 'url': 'https://www.w3schools.com/sql/', 'provider': 'W3Schools'}
    ],
    'docker': [
        {'title': 'Docker Documentation', 'url': 'https://docs.docker.com/', 'provider': 'Docker Inc.'}
    ],
    'kubernetes': [
        {'title': 'Kubernetes Documentation', 'url': 'https://kubernetes.io/docs/home/', 'provider': 'CNCF'}
    ],
    'aws': [
        {'title': 'AWS Documentation', 'url': 'https://docs.aws.amazon.com/', 'provider': 'AWS'}
    ],
    'git': [
        {'title': 'Pro Git Book', 'url': 'https://git-scm.com/book/en/v2', 'provider': 'Scott Chacon & Ben Straub'}
    ]
}

# ──────────────────────────────────────────────────────────────────────────────
# Role-specific YouTube search query templates
# Each role gets a specialised search pattern so the YouTube API returns
# content that matches the user's career path instead of generic tutorials.
# ──────────────────────────────────────────────────────────────────────────────

ROLE_YOUTUBE_QUERIES = {
    'frontend-dev': '{skill} frontend development tutorial {year}',
    'backend-dev': '{skill} backend server development tutorial {year}',
    'fullstack-dev': '{skill} full stack web development tutorial {year}',
    'data-scientist': '{skill} data science machine learning tutorial {year}',
    'devops-engineer': '{skill} devops CI/CD infrastructure tutorial {year}',
    'ml-engineer': '{skill} machine learning engineering production tutorial {year}',
    'cloud-architect': '{skill} cloud architecture enterprise tutorial {year}',
    'tech-lead': '{skill} software engineering leadership tutorial {year}'
}

class LearningService:
    """Learning resources and progress tracking service"""
    
    def __init__(self):
        self.db_service = FirestoreService()
    
    def get_learning_resources(self, skill_id: str, level: str = None, resource_type: str = None, role_title: str = None, role_id: str = None) -> List[Dict]:
        """Get learning resources for a specific skill, prioritizing/fetching role-specific ones"""
        try:
            filters = [('skillId', '==', skill_id)]
            
            if level:
                filters.append(('level', '==', level))
            
            if resource_type:
                filters.append(('type', '==', resource_type))
            
            resources = self.db_service.query_collection('learning_resources', filters)
            
            # Check if we have video resources for this skill matching the role. If not, fetch from YouTube API and cache them.
            role_videos = [r for r in resources if r.get('type') == 'video' and r.get('roleId') == role_id]
            if len(role_videos) < 2 and (not resource_type or resource_type == 'video') and role_title:
                friendly_name = skill_id.replace('-', ' ').replace('_', ' ').title()
                yt_videos = self.fetch_and_cache_youtube_videos(skill_id, friendly_name, role_title, role_id)
                if yt_videos:
                    resources.extend(yt_videos)
                    
            # Check if we have documentation resources for this skill matching the role. If not, generate and cache them.
            role_docs = [r for r in resources if r.get('type') in ['documentation', 'book', 'article'] and r.get('roleId') == role_id]
            if len(role_docs) < 2 and (not resource_type or resource_type != 'video') and role_title:
                new_docs = self.generate_and_cache_documentation_resources(skill_id, role_title, role_id)
                if new_docs:
                    resources.extend(new_docs)
            
            # Prioritize matching roleId first, then by rating/verified status
            resources.sort(key=lambda x: (
                x.get('roleId') == role_id if role_id else False,
                x.get('verified', False),
                x.get('rating', 0)
            ), reverse=True)
            
            return resources
            
        except Exception as e:
            logger.error(f"Error getting learning resources: {str(e)}")
            return []

    def fetch_and_cache_youtube_videos(self, skill_id: str, skill_name: str, role_title: str = None, role_id: str = None) -> List[Dict]:
        """Fetch videos from YouTube API for a skill and cache them in Firestore with role context"""
        def get_fallback_videos():
            friendly_name = skill_name or skill_id.replace('-', ' ').replace('_', ' ').title()
            fallback_videos = [
                {
                    'id': f"yt_{role_id or 'gen'}_{skill_id}_1",
                    'skillId': skill_id,
                    'roleId': role_id,
                    'roleTitle': role_title,
                    'title': f'{friendly_name} Essentials & Industry Best Practices',
                    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'type': 'video',
                    'duration': '25m',
                    'provider': 'TechAcademy',
                    'rating': 4.8,
                    'verified': True,
                    'level': 'beginner'
                },
                {
                    'id': f"yt_{role_id or 'gen'}_{skill_id}_2",
                    'skillId': skill_id,
                    'roleId': role_id,
                    'roleTitle': role_title,
                    'title': f'Complete {friendly_name} Masterclass for Professionals',
                    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'type': 'video',
                    'duration': '45m',
                    'provider': 'freeCodeCamp',
                    'rating': 4.9,
                    'verified': True,
                    'level': 'intermediate'
                }
            ]
            for video in fallback_videos:
                try:
                    self.db_service.create_document('learning_resources', video['id'], video)
                except Exception:
                    pass
            return fallback_videos

        api_key = os.environ.get('YOUTUBE_API_KEY')
        if not api_key:
            logger.warning("YOUTUBE_API_KEY not found in environment. Returning fallback videos.")
            return get_fallback_videos()
            
        try:
            from googleapiclient.discovery import build
            
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            # Build a role-specific search query from the templates
            current_year = datetime.utcnow().year
            if role_id and role_id in ROLE_YOUTUBE_QUERIES:
                query = ROLE_YOUTUBE_QUERIES[role_id].format(
                    skill=skill_name, year=current_year
                )
            elif role_title:
                query = f"{skill_name} for {role_title} tutorial {current_year}"
            else:
                query = f"{skill_name} tutorial beginner course {current_year}"
            
            logger.info(f"Fetching fresh YouTube videos for query: {query}")
            search_request = youtube.search().list(
                q=query,
                part='id,snippet',
                maxResults=3,
                order='relevance',
                type='video',
                safeSearch='strict'
            )
            
            search_response = search_request.execute()
            items = search_response.get('items', [])
            
            new_resources = []
            for item in items:
                video_id = item['id'].get('videoId')
                if not video_id:
                    continue
                    
                snippet = item.get('snippet', {})
                title = snippet.get('title', 'YouTube Tutorial')
                channel_title = snippet.get('channelTitle', 'YouTube')
                
                # Make the ID unique to the role so we cache separate links per role
                resource_id = f"yt_{role_id}_{video_id}" if role_id else f"yt_{video_id}"
                
                video_resource = {
                    'id': resource_id,
                    'skillId': skill_id,
                    'roleId': role_id,
                    'roleTitle': role_title,
                    'title': title,
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'type': 'video',
                    'duration': '20m', # Default duration approximation
                    'provider': channel_title,
                    'rating': 4.7,
                    'verified': True,
                    'level': 'beginner'
                }
                
                # Cache to firestore
                self.db_service.create_document('learning_resources', resource_id, video_resource)
                new_resources.append(video_resource)
                
            return new_resources
            
        except Exception as e:
            logger.error(f"Error fetching/caching YouTube videos for {skill_id}: {str(e)}")
            return get_fallback_videos()

    def generate_and_cache_documentation_resources(self, skill_id: str, role_title: str = None, role_id: str = None) -> List[Dict]:
        """Generate role-specific documentation resources for a skill and cache them in Firestore.
        
        Resolution order:
        1. ROLE_SPECIFIC_DOCS[role_id][skill_id]  – curated, role-aware docs
        2. GENERIC_DOCS_FALLBACK[skill_id]         – generic skill-level docs
        3. Auto-generated DevDocs link              – last resort
        """
        try:
            friendly_name = skill_id.replace('-', ' ').replace('_', ' ').title()
            
            # 1) Try role-specific docs first
            role_docs_map = ROLE_SPECIFIC_DOCS.get(role_id, {}) if role_id else {}
            mapped_docs = role_docs_map.get(skill_id.lower())
            
            # 2) Fall back to generic docs if nothing role-specific
            if not mapped_docs:
                mapped_docs = GENERIC_DOCS_FALLBACK.get(skill_id.lower())
            
            # 3) Ultimate fallback – auto-generated DevDocs link
            if not mapped_docs:
                mapped_docs = [
                    {
                        'title': f'{friendly_name} Developer Documentation',
                        'url': f'https://devdocs.io/{skill_id.lower()}/',
                        'provider': 'DevDocs'
                    }
                ]
                
            new_resources = []
            for i, doc in enumerate(mapped_docs):
                resource_id = f"doc_{role_id}_{skill_id}_{i+1}" if role_id else f"doc_{skill_id}_{i+1}"
                
                doc_resource = {
                    'id': resource_id,
                    'skillId': skill_id,
                    'roleId': role_id,
                    'roleTitle': role_title,
                    'title': doc['title'],
                    'url': doc['url'],
                    'type': 'documentation',
                    'duration': 'Self-paced',
                    'provider': doc['provider'],
                    'rating': 4.8,
                    'verified': True,
                    'level': 'intermediate'
                }
                
                # Cache to firestore
                self.db_service.create_document('learning_resources', resource_id, doc_resource)
                new_resources.append(doc_resource)
                
            return new_resources
            
        except Exception as e:
            logger.error(f"Error generating/caching documentation for {skill_id}: {str(e)}")
            return []
    
    def search_learning_resources(self, query: str, limit: int = 20) -> List[Dict]:
        """Search learning resources by title or provider"""
        try:
            # Get all resources (Firestore doesn't support full-text search natively)
            all_resources = self.db_service.query_collection('learning_resources')
            
            query_lower = query.lower()
            matching_resources = []
            
            for resource in all_resources:
                # Check title
                if query_lower in resource.get('title', '').lower():
                    matching_resources.append(resource)
                    continue
                
                # Check provider
                if query_lower in resource.get('provider', '').lower():
                    matching_resources.append(resource)
                    continue
                
                # Check skill name (if available)
                skill_name = resource.get('skillName', '')
                if query_lower in skill_name.lower():
                    matching_resources.append(resource)
            
            # Sort by relevance (verified first, then by rating)
            matching_resources.sort(key=lambda x: (x.get('verified', False), x.get('rating', 0)), reverse=True)
            
            return matching_resources[:limit]
            
        except Exception as e:
            logger.error(f"Error searching learning resources: {str(e)}")
            return []
    
    def get_resources_by_category(self, category: str, limit: int = 50) -> List[Dict]:
        """Get learning resources by skill category"""
        try:
            # First get skills in the category
            skills_in_category = self.db_service.query_collection(
                'skills_master', 
                [('category', '==', category)]
            )
            
            skill_ids = [skill['skillId'] for skill in skills_in_category]
            
            # Get resources for these skills
            all_resources = []
            for skill_id in skill_ids:
                resources = self.get_learning_resources(skill_id)
                all_resources.extend(resources)
            
            # Remove duplicates and sort
            unique_resources = []
            seen_urls = set()
            
            for resource in all_resources:
                url = resource.get('url', '')
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_resources.append(resource)
            
            # Sort by rating and verified status
            unique_resources.sort(key=lambda x: (x.get('verified', False), x.get('rating', 0)), reverse=True)
            
            return unique_resources[:limit]
            
        except Exception as e:
            logger.error(f"Error getting resources by category: {str(e)}")
            return []
    
    def mark_resource_completed(self, uid: str, resource_id: str, skill_id: str) -> bool:
        """Mark a learning resource as completed by user"""
        try:
            completion_data = {
                'uid': uid,
                'resourceId': resource_id,
                'skillId': skill_id,
                'completedAt': datetime.utcnow(),
                'source': 'user-reported'
            }
            
            # Create unique ID for completion record
            completion_id = f"{uid}_{resource_id}"
            
            success = self.db_service.create_document('learning_completions', completion_id, completion_data)
            
            if success:
                # Get resource details for logging
                resource = self.db_service.get_document('learning_resources', resource_id)
                resource_title = resource.get('title', 'Unknown Resource') if resource else 'Unknown Resource'
                
                # Log activity
                self.db_service.log_user_activity(
                    uid,
                    'LEARNING_COMPLETED',
                    f'Completed: {resource_title}'
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error marking resource completed: {str(e)}")
            return False
    
    def get_user_completions(self, uid: str, skill_id: str = None) -> List[Dict]:
        """Get user's completed learning resources"""
        try:
            filters = [('uid', '==', uid)]
            
            if skill_id:
                filters.append(('skillId', '==', skill_id))
            
            completions = self.db_service.query_collection('learning_completions', filters)
            
            # Enrich with resource details
            enriched_completions = []
            for completion in completions:
                resource_id = completion.get('resourceId')
                resource = self.db_service.get_document('learning_resources', resource_id)
                
                if resource:
                    enriched_completion = {
                        **completion,
                        'resource': resource
                    }
                    enriched_completions.append(enriched_completion)
            
            # Sort by completion date (most recent first)
            enriched_completions.sort(key=lambda x: x.get('completedAt', datetime.min), reverse=True)
            
            return enriched_completions
            
        except Exception as e:
            logger.error(f"Error getting user completions: {str(e)}")
            return []
    
    def get_learning_stats(self, uid: str) -> Dict:
        """Get user's learning statistics"""
        try:
            # Get all completions
            completions = self.get_user_completions(uid)
            
            # Calculate stats
            total_completed = len(completions)
            
            # Group by skill
            skills_learned = {}
            for completion in completions:
                skill_id = completion.get('skillId')
                if skill_id:
                    if skill_id not in skills_learned:
                        skills_learned[skill_id] = 0
                    skills_learned[skill_id] += 1
            
            # Group by resource type
            types_completed = {}
            for completion in completions:
                resource = completion.get('resource', {})
                resource_type = resource.get('type', 'unknown')
                if resource_type not in types_completed:
                    types_completed[resource_type] = 0
                types_completed[resource_type] += 1
            
            # Calculate total learning hours (estimated)
            total_hours = 0
            for completion in completions:
                resource = completion.get('resource', {})
                duration_str = resource.get('duration', '0h')
                
                # Simple parsing of duration (e.g., "2h", "30m", "1.5h")
                try:
                    if 'h' in duration_str:
                        hours = float(duration_str.replace('h', '').strip())
                        total_hours += hours
                    elif 'm' in duration_str:
                        minutes = float(duration_str.replace('m', '').strip())
                        total_hours += minutes / 60
                except:
                    pass  # Skip invalid duration formats
            
            return {
                'totalCompleted': total_completed,
                'uniqueSkills': len(skills_learned),
                'skillsBreakdown': skills_learned,
                'typesBreakdown': types_completed,
                'estimatedHours': round(total_hours, 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting learning stats: {str(e)}")
            return {
                'totalCompleted': 0,
                'uniqueSkills': 0,
                'skillsBreakdown': {},
                'typesBreakdown': {},
                'estimatedHours': 0
            }
    
    def get_recommended_resources(self, uid: str, limit: int = 10) -> List[Dict]:
        """Get recommended learning resources based on user's skills and roadmap"""
        try:
            # Get user's current skills
            user_skills = self.db_service.get_user_skills(uid)
            user_skill_ids = {skill['skillId'] for skill in user_skills}
            
            # Get user's active roadmap
            roadmap = self.db_service.get_user_roadmap(uid)
            
            # Extract role context from roadmap for role-specific resources
            role_id = roadmap.get('roleId') if roadmap else None
            role_title = roadmap.get('roleTitle', role_id.replace('-', ' ').title() if role_id else None) if roadmap else None
            
            recommended_resources = []
            
            if roadmap:
                # Get resources for roadmap skills
                milestones = roadmap.get('milestones', [])
                
                for milestone in milestones:
                    if milestone.get('completed', False):
                        continue  # Skip completed milestones
                    
                    skills = milestone.get('skills', [])
                    for skill in skills:
                        if skill.get('completed', False):
                            continue  # Skip completed skills
                        
                        skill_id = skill.get('skillId')
                        target_level = skill.get('targetLevel', 'intermediate')
                        
                        # Get resources for this skill WITH role context
                        resources = self.get_learning_resources(
                            skill_id, target_level,
                            role_title=role_title,
                            role_id=role_id
                        )
                        
                        # Add roadmap context to resources
                        for resource in resources[:2]:  # Limit per skill
                            resource_with_context = {
                                **resource,
                                'recommendationReason': f'Part of your {roadmap.get("roleId", "career")} roadmap',
                                'priority': skill.get('priority', 'medium'),
                                'milestoneTitle': milestone.get('title', 'Learning Milestone')
                            }
                            recommended_resources.append(resource_with_context)
            
            # If no roadmap or need more recommendations, suggest based on current skills
            if len(recommended_resources) < limit:
                for skill in user_skills:
                    skill_id = skill['skillId']
                    current_level = skill['level']
                    
                    # Suggest next level resources
                    next_level = self._get_next_level(current_level)
                    if next_level:
                        resources = self.get_learning_resources(skill_id, next_level)
                        
                        for resource in resources[:1]:  # One per skill
                            resource_with_context = {
                                **resource,
                                'recommendationReason': f'Advance your {skill_id} skills to {next_level}',
                                'priority': 'medium'
                            }
                            recommended_resources.append(resource_with_context)
                            
                            if len(recommended_resources) >= limit:
                                break
                    
                    if len(recommended_resources) >= limit:
                        break
            
            # Remove duplicates and limit results
            unique_resources = []
            seen_urls = set()
            
            for resource in recommended_resources:
                url = resource.get('url', '')
                if url not in seen_urls and len(unique_resources) < limit:
                    seen_urls.add(url)
                    unique_resources.append(resource)
            
            return unique_resources
            
        except Exception as e:
            logger.error(f"Error getting recommended resources: {str(e)}")
            return []
    
    def _get_next_level(self, current_level: str) -> Optional[str]:
        """Get the next proficiency level"""
        level_progression = {
            'beginner': 'intermediate',
            'intermediate': 'advanced',
            'advanced': None  # No next level
        }
        return level_progression.get(current_level)

    def set_learning_mode(self, uid: str, learning_mode: str) -> bool:
        """Set user's learning preference mode"""
        try:
            # Save to users collection
            success = self.db_service.update_document('users', uid, {'learningMode': learning_mode}, create_if_missing=True)
            if success:
                # Also sync to user_state collection to easily load on initial load
                self.db_service.update_document('user_state', uid, {'learningMode': learning_mode}, create_if_missing=True)
                logger.info(f"Successfully set learning mode '{learning_mode}' for user {uid}")
            return success
        except Exception as e:
            logger.error(f"Error setting learning mode: {str(e)}")
            return False