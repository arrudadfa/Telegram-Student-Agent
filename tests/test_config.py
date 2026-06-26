import config


def test_vestibulares_group_id():
    assert config.VESTIBULARES_GROUP_ID == -1001937153848


def test_brazil_timezone():
    assert str(config.BRAZIL_TZ) == "America/Sao_Paulo"


def test_news_model_is_str():
    assert isinstance(config.NEWS_MODEL, str) and config.NEWS_MODEL


def test_news_prompt_covers_three_themes():
    prompt = config.NEWS_SYSTEM_PROMPT
    assert "Concursos públicos federais" in prompt
    assert "Vestibulares" in prompt
    assert "Praticante de Prático" in prompt
    # Formatação Telegram: títulos de seção usam *negrito de uma estrela*, não headers "### Título"
    assert "*Concursos Públicos Federais*" in prompt
    assert "### Concursos" not in prompt
