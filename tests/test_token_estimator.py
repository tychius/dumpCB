from app.utils.token_estimator import estimate_text_tokens, _accurate_len

def test_estimator_basic():
    text = "Hello, world!" * 100
    approx = estimate_text_tokens(text)
    # never zero, always positive
    assert approx > 0
    # with tiktoken available, estimate should match exact
    exact = _accurate_len(text)
    if exact is not None:
        assert approx == exact 