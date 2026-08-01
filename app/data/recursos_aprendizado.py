"""Corpus de recursos de aprendizado por competência — consultado pelo rag_service.

Cada chave deve ser um substring (ou superstring) da competência que aparece em
`competencias_chave` das trilhas de carreira, para que o keyword matching do
rag_service funcione corretamente.
"""

RECURSOS_POR_COMPETENCIA: dict[str, list[dict]] = {
    # ------------------------------------------------------------------ Base
    "Lógica de programação": [
        {
            "titulo": "CS50x — Introduction to Computer Science (Harvard)",
            "url": "cs50.harvard.edu/x",
            "tipo": "curso",
            "gratuito": True,
        },
        {
            "titulo": "Exercism — Trilhas de prática em várias linguagens",
            "url": "exercism.org",
            "tipo": "plataforma",
            "gratuito": True,
        },
    ],
    "Algoritmos e estruturas de dados": [
        {
            "titulo": "Visualgo — Algoritmos e estruturas de dados animados",
            "url": "visualgo.net",
            "tipo": "ferramenta interativa",
            "gratuito": True,
        },
        {
            "titulo": "Estruturas de Dados e Algoritmos — freeCodeCamp",
            "url": "freecodecamp.org/learn/javascript-algorithms-and-data-structures",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Linguagens
    "Python": [
        {
            "titulo": "CS50P — Python (Harvard)",
            "url": "cs50.harvard.edu/python",
            "tipo": "curso",
            "gratuito": True,
        },
        {
            "titulo": "Automate the Boring Stuff with Python",
            "url": "automatetheboringstuff.com",
            "tipo": "livro online",
            "gratuito": True,
        },
        {
            "titulo": "Tutorial oficial do Python",
            "url": "docs.python.org/pt-br/3/tutorial",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    "JavaScript": [
        {
            "titulo": "The Modern JavaScript Tutorial (javascript.info)",
            "url": "javascript.info",
            "tipo": "tutorial",
            "gratuito": True,
        },
        {
            "titulo": "freeCodeCamp — JavaScript Algorithms and Data Structures",
            "url": "freecodecamp.org/learn/javascript-algorithms-and-data-structures",
            "tipo": "curso",
            "gratuito": True,
        },
        {
            "titulo": "Referência MDN JavaScript",
            "url": "developer.mozilla.org/pt-BR/docs/Web/JavaScript",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    "TypeScript": [
        {
            "titulo": "TypeScript Handbook (documentação oficial)",
            "url": "typescriptlang.org/docs/handbook",
            "tipo": "documentação",
            "gratuito": True,
        },
        {
            "titulo": "Total TypeScript — Matt Pocock (tutoriais gratuitos)",
            "url": "totaltypescript.com",
            "tipo": "tutorial",
            "gratuito": True,
        },
    ],
    "Java": [
        {
            "titulo": "Baeldung — Guias práticos de Java e Spring",
            "url": "baeldung.com",
            "tipo": "tutoriais",
            "gratuito": True,
        },
        {
            "titulo": "Oracle Java Tutorials (documentação oficial)",
            "url": "docs.oracle.com/javase/tutorial",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    "Kotlin": [
        {
            "titulo": "Kotlin Koans — exercícios interativos (JetBrains)",
            "url": "play.kotlinlang.org/koans",
            "tipo": "prática interativa",
            "gratuito": True,
        },
        {
            "titulo": "Android Basics with Compose (Google)",
            "url": "developer.android.com/courses/android-basics-compose/course",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Swift": [
        {
            "titulo": "Swift Playgrounds (Apple)",
            "url": "developer.apple.com/swift-playgrounds",
            "tipo": "app interativo",
            "gratuito": True,
        },
        {
            "titulo": "100 Days of SwiftUI (Paul Hudson)",
            "url": "hackingwithswift.com/100/swiftui",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "C#": [
        {
            "titulo": "Microsoft Learn — C# (documentação + trilhas)",
            "url": "learn.microsoft.com/pt-br/dotnet/csharp",
            "tipo": "documentação e curso",
            "gratuito": True,
        },
        {
            "titulo": "Unity Learn — C# para jogos",
            "url": "learn.unity.com",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "C/C++": [
        {
            "titulo": "cppreference.com — referência completa de C e C++",
            "url": "cppreference.com",
            "tipo": "documentação",
            "gratuito": True,
        },
        {
            "titulo": "CS50 — Semanas de C e ponteiros",
            "url": "cs50.harvard.edu/x",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Solidity": [
        {
            "titulo": "CryptoZombies — aprenda Solidity criando um jogo",
            "url": "cryptozombies.io",
            "tipo": "tutorial interativo",
            "gratuito": True,
        },
        {
            "titulo": "Documentação oficial do Solidity",
            "url": "docs.soliditylang.org",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Web front-end
    "HTML": [
        {
            "titulo": "MDN — Aprendendo desenvolvimento Web (HTML/CSS/JS)",
            "url": "developer.mozilla.org/pt-BR/docs/Learn",
            "tipo": "guia",
            "gratuito": True,
        },
        {
            "titulo": "The Odin Project — Foundations",
            "url": "theodinproject.com/paths/foundations",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "CSS": [
        {
            "titulo": "CSS-Tricks — guias e referências de CSS",
            "url": "css-tricks.com",
            "tipo": "referência e tutoriais",
            "gratuito": True,
        },
        {
            "titulo": "Flexbox Froggy — jogo para aprender Flexbox",
            "url": "flexboxfroggy.com",
            "tipo": "jogo interativo",
            "gratuito": True,
        },
    ],
    "React": [
        {
            "titulo": "React — documentação oficial (react.dev)",
            "url": "react.dev/learn",
            "tipo": "documentação e tutorial",
            "gratuito": True,
        },
        {
            "titulo": "Full Stack Open — React, Node.js, GraphQL (Universidade de Helsinki)",
            "url": "fullstackopen.com/pt",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Vue": [
        {
            "titulo": "Vue.js — documentação oficial com tutorial interativo",
            "url": "vuejs.org/tutorial",
            "tipo": "documentação e tutorial",
            "gratuito": True,
        },
    ],
    "Angular": [
        {
            "titulo": "Angular — Tutorial oficial (Tour of Heroes)",
            "url": "angular.dev/tutorials",
            "tipo": "tutorial",
            "gratuito": True,
        },
    ],
    "Design responsivo": [
        {
            "titulo": "freeCodeCamp — Responsive Web Design",
            "url": "freecodecamp.org/learn/2022/responsive-web-design",
            "tipo": "curso",
            "gratuito": True,
        },
        {
            "titulo": "MDN — Design responsivo",
            "url": "developer.mozilla.org/pt-BR/docs/Learn/CSS/CSS_layout/Responsive_Design",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Back-end / APIs
    "APIs REST": [
        {
            "titulo": "RESTful API Tutorial",
            "url": "restfulapi.net",
            "tipo": "guia",
            "gratuito": True,
        },
        {
            "titulo": "FastAPI — documentação oficial (Python)",
            "url": "fastapi.tiangolo.com/pt",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    "GraphQL": [
        {
            "titulo": "GraphQL — documentação oficial + tutorial How to GraphQL",
            "url": "graphql.org/learn",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    "Node.js": [
        {
            "titulo": "NodeSchool — workshops interativos de Node.js",
            "url": "nodeschool.io",
            "tipo": "tutoriais interativos",
            "gratuito": True,
        },
        {
            "titulo": "Full Stack Open — Node.js (Universidade de Helsinki)",
            "url": "fullstackopen.com/pt",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Autenticação e autorização": [
        {
            "titulo": "OWASP — Authentication Cheat Sheet",
            "url": "cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html",
            "tipo": "guia",
            "gratuito": True,
        },
        {
            "titulo": "JWT.io — introdução e depurador de tokens JWT",
            "url": "jwt.io/introduction",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Banco de dados
    "SQL e modelagem de banco de dados": [
        {
            "titulo": "SQLZoo — SQL interativo",
            "url": "sqlzoo.net",
            "tipo": "prática interativa",
            "gratuito": True,
        },
        {
            "titulo": "Mode SQL Tutorial",
            "url": "mode.com/sql-tutorial",
            "tipo": "tutorial",
            "gratuito": True,
        },
        {
            "titulo": "PostgreSQL Tutorial",
            "url": "postgresqltutorial.com",
            "tipo": "tutorial",
            "gratuito": True,
        },
    ],
    "PostgreSQL": [
        {
            "titulo": "PostgreSQL Tutorial",
            "url": "postgresqltutorial.com",
            "tipo": "tutorial",
            "gratuito": True,
        },
        {
            "titulo": "CS186 — Introduction to Database Systems (UC Berkeley, YouTube)",
            "url": "youtube.com/@CS186Berkeley",
            "tipo": "videoaula",
            "gratuito": True,
        },
    ],
    "MongoDB": [
        {
            "titulo": "MongoDB University — cursos oficiais gratuitos",
            "url": "learn.mongodb.com",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Performance tuning": [
        {
            "titulo": "Use The Index, Luke — SQL tuning para desenvolvedores",
            "url": "use-the-index-luke.com",
            "tipo": "livro online",
            "gratuito": True,
        },
    ],
    "Backup e recuperação": [
        {
            "titulo": "PostgreSQL — PITR e estratégias de backup (documentação oficial)",
            "url": "postgresql.org/docs/current/backup.html",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Engenharia de Dados
    "Apache Spark": [
        {
            "titulo": "Databricks Learning — curso gratuito de Apache Spark",
            "url": "learn.databricks.com/spark-fundamentals",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Apache Airflow": [
        {
            "titulo": "Apache Airflow — documentação oficial e tutorial",
            "url": "airflow.apache.org/docs/apache-airflow/stable/tutorial",
            "tipo": "documentação",
            "gratuito": True,
        },
        {
            "titulo": "Astronomer Academy — Airflow 101 (gratuito)",
            "url": "academy.astronomer.io",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "ETL": [
        {
            "titulo": "Fundamentals of Data Engineering (livro online parcialmente gratuito)",
            "url": "oreilly.com/library/view/fundamentals-of-data/9781098108298",
            "tipo": "livro",
            "gratuito": False,
        },
        {
            "titulo": "Airbyte — documentação e conceitos de EL(T)",
            "url": "docs.airbyte.com",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Data Science / IA / ML
    "Machine learning": [
        {
            "titulo": "fast.ai — Practical Deep Learning for Coders",
            "url": "fast.ai",
            "tipo": "curso",
            "gratuito": True,
        },
        {
            "titulo": "Google ML Crash Course",
            "url": "developers.google.com/machine-learning/crash-course",
            "tipo": "curso",
            "gratuito": True,
        },
        {
            "titulo": "Kaggle Learn — Machine Learning",
            "url": "kaggle.com/learn/intro-to-machine-learning",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Estatística": [
        {
            "titulo": "StatQuest with Josh Starmer (YouTube)",
            "url": "youtube.com/@statquest",
            "tipo": "videoaulas",
            "gratuito": True,
        },
        {
            "titulo": "Khan Academy — Estatística e probabilidade",
            "url": "khanacademy.org/math/statistics-probability",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Pandas": [
        {
            "titulo": "Pandas — Getting Started Tutorials (documentação oficial)",
            "url": "pandas.pydata.org/docs/getting_started/intro_tutorials",
            "tipo": "tutorial",
            "gratuito": True,
        },
        {
            "titulo": "Kaggle Learn — Pandas",
            "url": "kaggle.com/learn/pandas",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Jupyter Notebook": [
        {
            "titulo": "Try Jupyter — sem instalação, direto no browser",
            "url": "jupyter.org/try",
            "tipo": "ambiente online",
            "gratuito": True,
        },
        {
            "titulo": "Google Colab — notebooks gratuitos com GPU",
            "url": "colab.research.google.com",
            "tipo": "ambiente online",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ DevOps / Infra
    "Docker": [
        {
            "titulo": "Play with Docker — sandbox online gratuito",
            "url": "labs.play-with-docker.com",
            "tipo": "laboratório",
            "gratuito": True,
        },
        {
            "titulo": "Docker Getting Started",
            "url": "docs.docker.com/get-started",
            "tipo": "tutorial",
            "gratuito": True,
        },
    ],
    "Kubernetes": [
        {
            "titulo": "Play with Kubernetes — sandbox online gratuito",
            "url": "labs.play-with-k8s.com",
            "tipo": "laboratório",
            "gratuito": True,
        },
        {
            "titulo": "Kubernetes — documentação oficial com tutorial interativo",
            "url": "kubernetes.io/docs/tutorials",
            "tipo": "tutorial",
            "gratuito": True,
        },
    ],
    "CI/CD": [
        {
            "titulo": "GitHub Actions — documentação e exemplos iniciais",
            "url": "docs.github.com/pt/actions/learn-github-actions",
            "tipo": "documentação",
            "gratuito": True,
        },
        {
            "titulo": "GitLab CI/CD — tutorial para iniciantes",
            "url": "docs.gitlab.com/ee/ci/quick_start",
            "tipo": "tutorial",
            "gratuito": True,
        },
    ],
    "Linux": [
        {
            "titulo": "The Linux Command Line (William Shotts — livro gratuito online)",
            "url": "linuxcommand.org/tlcl.php",
            "tipo": "livro online",
            "gratuito": True,
        },
        {
            "titulo": "OverTheWire Bandit — Linux na prática via desafios",
            "url": "overthewire.org/wargames/bandit",
            "tipo": "desafio prático",
            "gratuito": True,
        },
    ],
    "Terraform": [
        {
            "titulo": "HashiCorp Learn — Terraform (tutoriais oficiais)",
            "url": "developer.hashicorp.com/terraform/tutorials",
            "tipo": "tutorial",
            "gratuito": True,
        },
    ],
    "AWS": [
        {
            "titulo": "AWS Skill Builder — cursos gratuitos da AWS",
            "url": "explore.skillbuilder.aws",
            "tipo": "curso",
            "gratuito": True,
        },
        {
            "titulo": "AWS Free Tier — experimentação prática gratuita",
            "url": "aws.amazon.com/pt/free",
            "tipo": "ambiente prático",
            "gratuito": True,
        },
    ],
    "Cloud": [
        {
            "titulo": "AWS Skill Builder — cursos gratuitos da AWS",
            "url": "explore.skillbuilder.aws",
            "tipo": "curso",
            "gratuito": True,
        },
        {
            "titulo": "Google Cloud Skills Boost — trilhas gratuitas",
            "url": "cloudskillsboost.google",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Monitoramento": [
        {
            "titulo": "Prometheus — Getting Started (documentação oficial)",
            "url": "prometheus.io/docs/introduction/getting_started",
            "tipo": "documentação",
            "gratuito": True,
        },
        {
            "titulo": "Grafana — Play — demo online sem instalação",
            "url": "play.grafana.org",
            "tipo": "demo",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Cibersegurança
    "Pentest": [
        {
            "titulo": "TryHackMe — plataforma de aprendizado prático em segurança",
            "url": "tryhackme.com",
            "tipo": "plataforma",
            "gratuito": True,
        },
        {
            "titulo": "Hack The Box Academy — trilhas gratuitas para iniciantes",
            "url": "academy.hackthebox.com",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "OWASP": [
        {
            "titulo": "OWASP Top 10 — guia oficial das 10 principais vulnerabilidades",
            "url": "owasp.org/Top10",
            "tipo": "guia",
            "gratuito": True,
        },
        {
            "titulo": "OWASP WebGoat — laboratório prático de vulnerabilidades web",
            "url": "owasp.org/www-project-webgoat",
            "tipo": "laboratório",
            "gratuito": True,
        },
    ],
    "Criptografia": [
        {
            "titulo": "Cryptopals — desafios de criptografia aplicada",
            "url": "cryptopals.com",
            "tipo": "desafio prático",
            "gratuito": True,
        },
        {
            "titulo": "Practical Cryptography for Developers (livro online gratuito)",
            "url": "cryptobook.nakov.com",
            "tipo": "livro online",
            "gratuito": True,
        },
    ],
    "Redes TCP/IP": [
        {
            "titulo": "Cisco Networking Academy — cursos gratuitos (Networking Essentials)",
            "url": "netacad.com/courses/networking",
            "tipo": "curso",
            "gratuito": True,
        },
        {
            "titulo": "Computer Networking: A Top-Down Approach (Kurose & Ross — vídeos gratuitos)",
            "url": "gaia.cs.umass.edu/kurose_ross/videos.php",
            "tipo": "videoaulas",
            "gratuito": True,
        },
    ],
    "Firewalls": [
        {
            "titulo": "Cisco NetAcad — Network Security (parcialmente gratuito)",
            "url": "netacad.com/courses/security",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "ISO 27001": [
        {
            "titulo": "IT Governance — introdução gratuita à ISO 27001",
            "url": "itgovernance.co.uk/iso27001",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "LGPD": [
        {
            "titulo": "ANPD — materiais educativos oficiais sobre LGPD",
            "url": "gov.br/anpd/pt-br/assuntos/noticias/materiais-educativos",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Qualidade / Testes
    "Testes automatizados": [
        {
            "titulo": "Test Automation University (Applitools — cursos gratuitos)",
            "url": "testautomationu.applitools.com",
            "tipo": "curso",
            "gratuito": True,
        },
        {
            "titulo": "Pytest — documentação oficial com tutorial",
            "url": "docs.pytest.org/en/stable/getting-started.html",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    "Selenium": [
        {
            "titulo": "Selenium — documentação e guia de início rápido",
            "url": "selenium.dev/documentation",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    "BDD": [
        {
            "titulo": "Cucumber — guia de BDD para iniciantes",
            "url": "cucumber.io/docs/guides/overview",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "Postman": [
        {
            "titulo": "Postman Learning Center",
            "url": "learning.postman.com",
            "tipo": "documentação e tutoriais",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ UX / UI
    "Figma": [
        {
            "titulo": "Figma Learn — tutoriais oficiais (vídeos gratuitos)",
            "url": "figma.com/resource-library/figma-tutorial-for-beginners",
            "tipo": "tutorial",
            "gratuito": True,
        },
    ],
    "Pesquisa com usuários": [
        {
            "titulo": "Nielsen Norman Group — artigos gratuitos sobre UX research",
            "url": "nngroup.com/articles",
            "tipo": "artigos",
            "gratuito": True,
        },
        {
            "titulo": "Google UX Design Certificate — introdução à pesquisa (Coursera, audit gratuito)",
            "url": "coursera.org/professional-certificates/google-ux-design",
            "tipo": "curso",
            "gratuito": False,
        },
    ],
    "Acessibilidade web": [
        {
            "titulo": "W3C — Web Accessibility Initiative (WAI) — guia completo",
            "url": "w3.org/WAI/fundamentals",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "Prototipagem": [
        {
            "titulo": "Figma Learn — protótipos interativos",
            "url": "figma.com/resource-library/prototyping-in-figma",
            "tipo": "tutorial",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Mobile
    "React Native": [
        {
            "titulo": "React Native — documentação oficial com tutorial",
            "url": "reactnative.dev/docs/getting-started",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    "Flutter": [
        {
            "titulo": "Flutter Codelabs — tutoriais práticos oficiais",
            "url": "docs.flutter.dev/codelabs",
            "tipo": "tutorial",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Gestão / Agile
    "Scrum": [
        {
            "titulo": "Scrum Guide — guia oficial do Scrum (gratuito, em português)",
            "url": "scrumguides.org/docs/scrumguide/v2020/2020-Scrum-Guide-PortugueseBR.pdf",
            "tipo": "guia",
            "gratuito": True,
        },
        {
            "titulo": "Scrum.org — Open Assessments gratuitos para praticar",
            "url": "scrum.org/open-assessments",
            "tipo": "simulados",
            "gratuito": True,
        },
    ],
    "Kanban": [
        {
            "titulo": "Kanban Guide (Agile Alliance)",
            "url": "agilealliance.org/what-is-kanban",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "OKRs": [
        {
            "titulo": "What Matters — introdução a OKRs por John Doerr",
            "url": "whatmatters.com/resources/google-okr-playbook",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "User stories": [
        {
            "titulo": "Mountain Goat Software — guia de user stories",
            "url": "mountaingoatsoftware.com/agile/user-stories",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "Métricas de produto": [
        {
            "titulo": "Mixpanel — Product Analytics Guide (gratuito)",
            "url": "mixpanel.com/blog/product-analytics",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Ferramentas transversais
    "Git": [
        {
            "titulo": "Pro Git Book (livro gratuito online)",
            "url": "git-scm.com/book/pt-br/v2",
            "tipo": "livro online",
            "gratuito": True,
        },
        {
            "titulo": "Learn Git Branching — tutorial interativo visual",
            "url": "learngitbranching.js.org/?locale=pt_BR",
            "tipo": "tutorial interativo",
            "gratuito": True,
        },
    ],
    "Power BI": [
        {
            "titulo": "Microsoft Learn — Trilha Power BI (cursos gratuitos)",
            "url": "learn.microsoft.com/pt-br/training/powerplatform/power-bi",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Tableau": [
        {
            "titulo": "Tableau Public — treino prático com dados reais",
            "url": "public.tableau.com/app/resources/learn",
            "tipo": "plataforma",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Desenvolvimento de jogos
    "Unity": [
        {
            "titulo": "Unity Learn — trilhas oficiais para iniciantes",
            "url": "learn.unity.com",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Unreal Engine": [
        {
            "titulo": "Unreal Online Learning — cursos oficiais gratuitos",
            "url": "dev.epicgames.com/community/learning",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ IoT / Embarcados
    "Arduino": [
        {
            "titulo": "Arduino Project Hub — projetos e tutoriais gratuitos",
            "url": "projecthub.arduino.cc",
            "tipo": "projetos práticos",
            "gratuito": True,
        },
        {
            "titulo": "Arduino Getting Started (documentação oficial)",
            "url": "docs.arduino.cc/learn/starting-guide/getting-started-arduino",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    "Raspberry Pi": [
        {
            "titulo": "Raspberry Pi Learning Hub — projetos e tutoriais gratuitos",
            "url": "projects.raspberrypi.org",
            "tipo": "projetos práticos",
            "gratuito": True,
        },
    ],
    "MQTT": [
        {
            "titulo": "HiveMQ — MQTT Essentials (guia completo e gratuito)",
            "url": "hivemq.com/mqtt-essentials",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Blockchain / Web3
    "Smart contracts": [
        {
            "titulo": "CryptoZombies — aprenda Solidity e smart contracts",
            "url": "cryptozombies.io",
            "tipo": "tutorial interativo",
            "gratuito": True,
        },
        {
            "titulo": "Ethereum Developer Docs — guia oficial",
            "url": "ethereum.org/pt-br/developers/docs",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    "Web3": [
        {
            "titulo": "Ethereum.org — trilha de aprendizado",
            "url": "ethereum.org/pt-br/learn",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Soft skills técnicas
    "Programação orientada a objetos": [
        {
            "titulo": "Refactoring Guru — Design Patterns (gratuito)",
            "url": "refactoring.guru/pt-br/design-patterns",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "Design Patterns": [
        {
            "titulo": "Refactoring Guru — padrões de projeto em Python/Java/etc.",
            "url": "refactoring.guru/pt-br/design-patterns",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "Microsserviços": [
        {
            "titulo": "Martin Fowler — Microservices Guide",
            "url": "martinfowler.com/microservices",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "Arquitetura de software": [
        {
            "titulo": "Martin Fowler — Software Architecture Guide",
            "url": "martinfowler.com/architecture",
            "tipo": "guia",
            "gratuito": True,
        },
        {
            "titulo": "The Architecture of Open Source Applications",
            "url": "aosabook.org",
            "tipo": "livro online",
            "gratuito": True,
        },
    ],
    "Engenharia de software": [
        {
            "titulo": "The Twelve-Factor App",
            "url": "12factor.net/pt_br",
            "tipo": "guia",
            "gratuito": True,
        },
        {
            "titulo": "Software Engineering at Google (livro online)",
            "url": "abseil.io/resources/swe-book",
            "tipo": "livro online",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Dados (complementos)
    "SQL": [
        {
            "titulo": "SQLBolt — SQL interativo do zero",
            "url": "sqlbolt.com",
            "tipo": "tutorial interativo",
            "gratuito": True,
        },
        {
            "titulo": "Use The Index, Luke — SQL e índices (avançado)",
            "url": "use-the-index-luke.com",
            "tipo": "livro online",
            "gratuito": True,
        },
    ],
    "Bancos de dados": [
        {
            "titulo": "CS50 SQL (Harvard)",
            "url": "cs50.harvard.edu/sql",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Modelagem de dados": [
        {
            "titulo": "dbdiagram.io — modelagem visual de bancos",
            "url": "dbdiagram.io",
            "tipo": "ferramenta",
            "gratuito": True,
        },
        {
            "titulo": "Database Design Course — freeCodeCamp",
            "url": "freecodecamp.org/news/database-design-course",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Visualização de dados": [
        {
            "titulo": "Storytelling with Data — blog",
            "url": "storytellingwithdata.com/blog",
            "tipo": "blog",
            "gratuito": True,
        },
        {
            "titulo": "From Data to Viz — escolha do gráfico certo",
            "url": "data-to-viz.com",
            "tipo": "guia interativo",
            "gratuito": True,
        },
    ],
    "Excel": [
        {
            "titulo": "Excel Easy — tutoriais do básico ao avançado",
            "url": "excel-easy.com",
            "tipo": "tutorial",
            "gratuito": True,
        },
        {
            "titulo": "Treinamento de Excel — Microsoft Support",
            "url": "support.microsoft.com/excel",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Gestão / produto / soft skills
    "Metodologias ágeis": [
        {
            "titulo": "Manifesto Ágil",
            "url": "agilemanifesto.org/iso/ptbr",
            "tipo": "referência",
            "gratuito": True,
        },
        {
            "titulo": "Atlassian Agile Coach",
            "url": "atlassian.com/agile",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "Ferramentas ágeis": [
        {
            "titulo": "Jira — guias oficiais (Atlassian)",
            "url": "atlassian.com/software/jira/guides",
            "tipo": "guia",
            "gratuito": True,
        },
        {
            "titulo": "Trello — guia de uso",
            "url": "trello.com/guide",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "Priorização e roadmap": [
        {
            "titulo": "ProductPlan — guia de roadmaps de produto",
            "url": "productplan.com/learn",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "Comunicação": [
        {
            "titulo": "Google Technical Writing — comunicação técnica",
            "url": "developers.google.com/tech-writing",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Liderança": [
        {
            "titulo": "Google re:Work — guia de gestão e liderança",
            "url": "rework.withgoogle.com/guides",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "Trabalho em equipe": [
        {
            "titulo": "Atlassian Team Playbook",
            "url": "atlassian.com/team-playbook",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "Resolução de problemas": [
        {
            "titulo": "Codewars — prática de resolução de problemas",
            "url": "codewars.com",
            "tipo": "plataforma",
            "gratuito": True,
        },
    ],
    "Negociação": [
        {
            "titulo": "Harvard PON — artigos sobre negociação",
            "url": "pon.harvard.edu/category/daily",
            "tipo": "blog",
            "gratuito": True,
        },
    ],
    "Inglês técnico": [
        {
            "titulo": "BBC Learning English",
            "url": "bbc.co.uk/learningenglish",
            "tipo": "plataforma",
            "gratuito": True,
        },
    ],
    "Gestão de riscos": [
        {
            "titulo": "ISO 31000 — visão geral de gestão de riscos",
            "url": "iso.org/iso-31000-risk-management.html",
            "tipo": "referência",
            "gratuito": True,
        },
    ],
    "Atendimento ao cliente": [
        {
            "titulo": "HubSpot Academy — Customer Service",
            "url": "academy.hubspot.com/courses",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Documentação técnica": [
        {
            "titulo": "Write the Docs — guia de documentação",
            "url": "writethedocs.org/guide",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Front-end / mobile (complementos)
    "Gerenciamento de estado": [
        {
            "titulo": "React — Gerenciando o estado (react.dev)",
            "url": "react.dev/learn/managing-state",
            "tipo": "documentação",
            "gratuito": True,
        },
        {
            "titulo": "Redux Essentials",
            "url": "redux.js.org/tutorials/essentials/part-1-overview-concepts",
            "tipo": "tutorial",
            "gratuito": True,
        },
    ],
    "Publicação em lojas de aplicativos": [
        {
            "titulo": "Distribuir apps — Google Play (Android)",
            "url": "developer.android.com/distribute",
            "tipo": "documentação",
            "gratuito": True,
        },
        {
            "titulo": "Submitting apps — App Store (Apple)",
            "url": "developer.apple.com/app-store/submitting",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    "Design system": [
        {
            "titulo": "Material Design 3 (Google)",
            "url": "m3.material.io",
            "tipo": "guia",
            "gratuito": True,
        },
        {
            "titulo": "Design Systems 101 — Nielsen Norman Group",
            "url": "nngroup.com/articles/design-systems-101",
            "tipo": "artigo",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Cloud (por provedor) e suporte
    "Azure": [
        {
            "titulo": "Microsoft Learn — Azure Fundamentals",
            "url": "learn.microsoft.com/training/azure",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "GCP": [
        {
            "titulo": "Google Cloud Skills Boost",
            "url": "cloudskillsboost.google",
            "tipo": "plataforma",
            "gratuito": True,
        },
    ],
    "Hardware de computadores": [
        {
            "titulo": "Crash Course Computer Science (YouTube)",
            "url": "youtube.com/playlist?list=PL8dPuuaLjXtNlUrzyH5r6jN9ulIgZBpdo",
            "tipo": "vídeo",
            "gratuito": True,
        },
    ],
    "Blockchain": [
        {
            "titulo": "Ethereum.org — Desenvolvedores",
            "url": "ethereum.org/pt-br/developers",
            "tipo": "documentação",
            "gratuito": True,
        },
    ],
    "APIs e integrações": [
        {
            "titulo": "Postman Learning Center",
            "url": "learning.postman.com",
            "tipo": "documentação",
            "gratuito": True,
        },
        {
            "titulo": "REST API Tutorial",
            "url": "restfulapi.net",
            "tipo": "tutorial",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Infra / redes (complementos)
    "Virtualização": [
        {
            "titulo": "Docker — Getting Started (containers)",
            "url": "docs.docker.com/get-started",
            "tipo": "tutorial",
            "gratuito": True,
        },
    ],
    "Segurança de infraestrutura": [
        {
            "titulo": "CIS Benchmarks — hardening de sistemas",
            "url": "cisecurity.org/cis-benchmarks",
            "tipo": "referência",
            "gratuito": True,
        },
    ],
    "Switches e roteadores": [
        {
            "titulo": "Cisco Networking Academy",
            "url": "netacad.com",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Cabeamento estruturado": [
        {
            "titulo": "Cisco Networking Academy — fundamentos de redes",
            "url": "netacad.com",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Certificações de rede (CCNA)": [
        {
            "titulo": "Cisco Networking Academy — preparação CCNA",
            "url": "netacad.com/courses/networking",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Jogos / IoT (complementos)
    "Matemática para jogos": [
        {
            "titulo": "Math for Game Developers (YouTube)",
            "url": "youtube.com/playlist?list=PLW3Zl3wyJwWOpdhYedlD-yCB7WQoHf-My",
            "tipo": "vídeo",
            "gratuito": True,
        },
    ],
    "Eletrônica": [
        {
            "titulo": "All About Circuits — eletrônica do zero",
            "url": "allaboutcircuits.com/textbook",
            "tipo": "livro online",
            "gratuito": True,
        },
    ],
    # ------------------------------------------------------------------ Gestão / pré-vendas / governança (complementos)
    "Facilitação de reuniões": [
        {
            "titulo": "Atlassian Team Playbook — facilitação",
            "url": "atlassian.com/team-playbook/plays",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "Resolução de conflitos": [
        {
            "titulo": "MindTools — Resolução de Conflitos",
            "url": "mindtools.com/conflict-resolution",
            "tipo": "artigo",
            "gratuito": True,
        },
    ],
    "Métricas ágeis": [
        {
            "titulo": "Atlassian — Agile metrics",
            "url": "atlassian.com/agile/project-management/metrics",
            "tipo": "guia",
            "gratuito": True,
        },
    ],
    "CRM": [
        {
            "titulo": "HubSpot Academy — CRM",
            "url": "academy.hubspot.com/courses/hubspot-crm",
            "tipo": "curso",
            "gratuito": True,
        },
    ],
    "Auditoria de TI": [
        {
            "titulo": "ISACA — recursos de auditoria e governança",
            "url": "isaca.org/resources",
            "tipo": "referência",
            "gratuito": True,
        },
    ],
}
