"""Prompt e ferramenta (tool use) da extração do perfil estruturado ao final da triagem."""

from typing import Any

PROMPT_GERAR_PERFIL = """\
Você é um mentor de carreira especializado em estudantes de Sistemas de Informação. \
Com base em toda a conversa de triagem abaixo, extraia e estruture o perfil do aluno \
chamando a ferramenta `salvar_perfil_aluno` com um JSON completo e consistente. \
Preencha todos os campos da melhor forma possível a partir do que foi dito; quando uma \
informação não tiver sido mencionada, utilize uma string vazia ou lista vazia conforme \
o tipo do campo.

REGRA CENTRAL — não invente nada: registre apenas o que o aluno disse ou o que é \
consequência direta e inequívoca disso. Nunca acrescente tecnologias, ferramentas, \
produtos, resultados, experiências ou níveis de conhecimento que o aluno não mencionou. \
Na dúvida, use o termo genérico que o próprio aluno usou.

Anos e datas (certificações, experiências, previsão de conclusão): registre exatamente o \
ano que o aluno informou, inclusive anos recentes, o ano corrente ou um futuro próximo. \
Não "corrija" nem ajuste o ano por achar que está errado. Se o aluno NÃO informou o ano de \
uma certificação/experiência, deixe o campo `ano` em branco ("") — NUNCA preencha com um \
ano inventado (ex.: 2024). Use o "Contexto temporal" fornecido para saber qual é o ano atual.

Atenção aos campos `formacao`, `certificacoes` e `links`: preencha apenas com o que o \
aluno mencionou explicitamente (nome da instituição, certificações com curso/ano, URLs \
de GitHub/LinkedIn/portfólio). Para `experiencias[].resultados`, registre apenas \
resultados, números ou impactos que o aluno tenha citado (ex.: "usado por X pessoas", \
"reduziu o tempo de Y"); deixe como string vazia se nada foi dito sobre resultado.

Para o campo `resumo_geral`, escreva de 3 a 4 frases que funcionem como pitch \
profissional: (1) quem é o aluno e qual área ele almeja, (2) o que ele já sabe ou \
construiu de mais relevante, (3) seu objetivo imediato de carreira. Use linguagem \
ativa e específica; evite frases genéricas como "estudante dedicado", "apaixonado \
por tecnologia" ou "em busca de oportunidades". O tom deve ser compatível com as \
áreas em `objetivo_carreira.areas_interesse`.

Ao preencher `stack_tecnica`, você só pode inferir uma tecnologia quando ela for \
**consequência necessária e inequívoca** de algo que o aluno nomeou — por exemplo, quem \
disse "construí uma API com Django" usa Python (Django é um framework Python); quem citou \
"React" usa JavaScript. Nesses casos, inclua apenas a tecnologia realmente implicada. \
É PROIBIDO acrescentar produtos, fornecedores, variantes, dialetos ou versões específicas \
que o aluno não citou: se ele disse apenas "SQL", NÃO transforme em "SQL Server", \
"PostgreSQL" ou "MySQL"; se disse "banco de dados", NÃO escolha um SGBD específico; se disse \
"nuvem", NÃO adicione "AWS" ou "Azure". Registre o termo genérico que o próprio aluno usou. \
Preserve também o nível declarado: se ele disse ter conhecimento "básico" em algo, não o \
descreva como domínio avançado. Na dúvida entre inventar e omitir, omita.

Para cada item em `stack_tecnica.linguagens` e `stack_tecnica.frameworks_ferramentas`, \
declare o `nivel` do aluno naquela tecnologia usando um destes valores: "" (vazio, se ele \
não sinalizou nível algum), "basico" (mexeu pouco, ainda aprendendo), "intermediario" \
(usou em pelo menos um projeto real do começo ao fim) ou "avancado" (usa com autonomia em \
projetos mais complexos ou estágio). Se o aluno disse "básico em SQL", registre \
{"nome": "SQL", "nivel": "basico"}. NÃO promova de nível: se ele disse "básico", jamais \
escreva "avancado". Se ele mencionou a tecnologia sem falar de nível, use "" (vazio).

Para `areas_afinidade`, com base em TODA a conversa (interesses, stack, experiências e \
objetivos), sugira de 2 a 4 áreas da tecnologia que combinam com o perfil do aluno. Para \
cada uma, escreva em `porque` uma frase curta explicando por que faz sentido para ELE, \
citando algo concreto que ele trouxe. Enquadre como possibilidades a explorar, não como um \
veredito — tom de convite, não de rótulo definitivo. Baseie-se apenas no que o aluno disse; \
não invente interesses. Use nomes de áreas reconhecíveis (ex.: "Desenvolvimento Back-end", \
"Ciência de Dados", "Segurança da Informação", "Desenvolvimento Mobile").

Escreva todos os textos em texto corrido simples, sem Markdown (sem asteriscos, hífens de \
lista ou `#`).
"""

FERRAMENTA_PERFIL: dict[str, Any] = {
    "name": "salvar_perfil_aluno",
    "description": "Salva o perfil estruturado do aluno extraído da conversa de triagem.",
    "input_schema": {
        "type": "object",
        "properties": {
            "objetivo_carreira": {
                "type": "object",
                "properties": {
                    "curto_prazo": {"type": "string"},
                    "medio_prazo": {"type": "string"},
                    "areas_interesse": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["curto_prazo", "medio_prazo", "areas_interesse"],
            },
            "experiencias": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tipo": {
                            "type": "string",
                            "enum": [
                                "estagio",
                                "freela",
                                "projeto_pessoal",
                                "projeto_academico",
                                "voluntariado",
                            ],
                        },
                        "titulo": {"type": "string"},
                        "descricao": {"type": "string"},
                        "periodo": {"type": "string"},
                        "tecnologias": {"type": "array", "items": {"type": "string"}},
                        "resultados": {"type": "string"},
                    },
                    "required": ["tipo", "titulo", "descricao", "periodo", "tecnologias", "resultados"],
                },
            },
            "disciplinas_relevantes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "nome": {"type": "string"},
                        "relevancia": {"type": "string"},
                    },
                    "required": ["nome", "relevancia"],
                },
            },
            "stack_tecnica": {
                "type": "object",
                "properties": {
                    "linguagens": {
                        "type": "array",
                        "description": "Linguagens de programação com o nível declarado.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "nome": {"type": "string"},
                                "nivel": {
                                    "type": "string",
                                    "description": "Nível declarado ou inferido pelo aluno. Vazio se não indicou.",
                                    "enum": ["", "basico", "intermediario", "avancado"],
                                },
                            },
                            "required": ["nome", "nivel"],
                        },
                    },
                    "frameworks_ferramentas": {
                        "type": "array",
                        "description": "Frameworks, bibliotecas ou ferramentas com o nível declarado.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "nome": {"type": "string"},
                                "nivel": {
                                    "type": "string",
                                    "enum": ["", "basico", "intermediario", "avancado"],
                                },
                            },
                            "required": ["nome", "nivel"],
                        },
                    },
                },
                "required": ["linguagens", "frameworks_ferramentas"],
            },
            "soft_skills": {"type": "array", "items": {"type": "string"}},
            "restricoes": {
                "type": "object",
                "properties": {
                    "carga_horaria_disponivel": {"type": "string"},
                    "localizacao": {"type": "string"},
                    "modalidade_preferida": {
                        "type": "string",
                        "enum": ["presencial", "remoto", "hibrido", "indiferente"],
                    },
                    "outras": {"type": "string"},
                },
                "required": [
                    "carga_horaria_disponivel",
                    "localizacao",
                    "modalidade_preferida",
                    "outras",
                ],
            },
            "resumo_geral": {"type": "string"},
            "formacao": {
                "type": "object",
                "properties": {
                    "instituicao": {"type": "string"},
                    "previsao_conclusao": {"type": "string"},
                    "destaques_academicos": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["instituicao", "previsao_conclusao", "destaques_academicos"],
            },
            "certificacoes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "nome": {"type": "string"},
                        "instituicao": {"type": "string"},
                        "ano": {"type": "string"},
                    },
                    "required": ["nome", "instituicao", "ano"],
                },
            },
            "links": {
                "type": "object",
                "properties": {
                    "github": {"type": "string"},
                    "linkedin": {"type": "string"},
                    "portfolio": {"type": "string"},
                    "outro": {"type": "string"},
                },
                "required": ["github", "linkedin", "portfolio", "outro"],
            },
            "areas_afinidade": {
                "type": "array",
                "description": "2 a 4 áreas da tecnologia que combinam com o perfil do aluno.",
                "items": {
                    "type": "object",
                    "properties": {
                        "area": {"type": "string"},
                        "porque": {"type": "string"},
                    },
                    "required": ["area", "porque"],
                },
            },
        },
        "required": [
            "objetivo_carreira",
            "experiencias",
            "disciplinas_relevantes",
            "stack_tecnica",
            "soft_skills",
            "restricoes",
            "resumo_geral",
            "formacao",
            "certificacoes",
            "links",
            "areas_afinidade",
        ],
    },
    "cache_control": {"type": "ephemeral"},
}
