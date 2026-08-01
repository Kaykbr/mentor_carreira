"""Mapa de sinônimos/variantes de competências técnicas — consultado por `competencias.py`.

Cada entrada associa uma forma canônica (chave, em minúsculas) a variantes equivalentes
que aparecem na fala dos alunos ou no corpus de recursos de aprendizado. O
matching de `app/services/competencias.py` usa estes grupos para tratar "JS" e
"JavaScript" (ou "Node.js" e "nodejs") como a mesma competência.

Regras de curadoria:
- Tudo em minúsculas; o normalizador já faz `.strip().lower()`.
- Evite variantes de 1 caractere ou ambíguas (ex.: "r", "go", "c") — gerariam falsos
  positivos no matching por substring.
- Mantenha foco na stack que aparece no corpus de `recursos_aprendizado.py` (usado pelo RAG).
"""

# forma canônica -> lista de variantes equivalentes
SINONIMOS: dict[str, list[str]] = {
    # Linguagens
    "javascript": ["js", "ecmascript", "java script"],
    "typescript": ["ts"],
    "node.js": ["nodejs", "node js", "node"],
    "c#": ["csharp", "c sharp", "c-sharp", "dotnet", ".net"],
    "c++": ["cpp", "c plus plus", "cplusplus"],
    "python": ["py"],
    "golang": ["go lang"],
    # Front-end
    "react": ["reactjs", "react.js"],
    "react native": ["reactnative", "rn"],
    "vue": ["vuejs", "vue.js"],
    "angular": ["angularjs", "angular.js"],
    "design responsivo": ["responsividade", "responsivo", "design adaptativo", "layout responsivo"],
    "acessibilidade web": ["a11y", "acessibilidade"],
    # Back-end / dados
    "postgresql": ["postgres", "postgre", "psql"],
    "sql": ["t-sql", "tsql", "pl/sql", "plsql"],
    "mongodb": ["mongo"],
    "apis rest": ["api rest", "rest", "restful", "consumo de apis rest"],
    "graphql": ["graph ql"],
    # DevOps / infra
    "kubernetes": ["k8s"],
    "ci/cd": ["cicd", "integração contínua", "ci cd", "pipeline ci/cd"],
    "infrastructure as code": ["iac", "infraestrutura como código", "terraform"],
    "aws": ["amazon web services"],
    "gcp": ["google cloud", "google cloud platform"],
    "azure": ["microsoft azure"],
    # Dados / IA
    "machine learning": ["ml", "aprendizado de máquina", "aprendizado de maquina"],
    "pandas": ["pandas python"],
    "power bi": ["powerbi", "power-bi"],
    "apache spark": ["spark"],
    "apache airflow": ["airflow"],
    "performance tuning": ["otimização de performance", "otimizacao de performance", "tuning"],
    # Qualidade / testes
    "testes automatizados": ["qa", "testes de software", "testes manuais", "automação de testes"],
    # Blockchain
    "smart contracts": ["contratos inteligentes", "contrato inteligente"],
    # Áreas de carreira — variantes de idioma/grafia para o recomendador
    "cibersegurança": [
        "cybersecurity", "cyber security", "segurança da informação",
        "seguranca da informacao", "segurança cibernética", "seguranca cibernetica",
        "infosec", "ethical hacking", "hacking etico",
    ],
    "inteligência artificial": [
        "inteligencia artificial", "ia e ml", "ia/ml", "machine learning e ia",
        "artificial intelligence",
    ],
    # Cibersegurança — competências específicas
    "pentest": ["teste de intrusão", "teste de penetração", "penetration testing", "pen test"],
    "owasp": ["segurança de aplicações", "seguranca de aplicacoes"],
    "redes tcp/ip": [
        "tcp/ip",
        "tcp ip",
        "protocolos de rede",
        "redes de computadores",
        "redes e segurança",
        "redes e seguranca",
    ],
    # Gestão / ágil
    "scrum": ["scrum master"],
    "metodologias ágeis": ["metodologias ageis", "agile", "ágil", "agil", "métodos ágeis"],
    "user stories": ["histórias de usuário", "historias de usuario", "escrita de requisitos"],
    # Ferramentas transversais
    "git": ["controle de versão", "controle de versao", "versionamento", "github", "gitlab"],
    "programação orientada a objetos": ["poo", "oop", "orientação a objetos", "orientacao a objetos"],
    # Arquitetura / governança (formas alternativas)
    "arquitetura de software": ["arquitetura de soluções", "arquitetura de solucoes"],
    "documentação técnica": ["documentação de processos", "documentacao de processos", "documentação"],
}
