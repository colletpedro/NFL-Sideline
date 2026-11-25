"""Modelos do hub (um módulo por modelo). `MODELS` mapeia a chave do CLI ao módulo, que deve expor
`cmd_backtest`, `cmd_register`, `cmd_predict` e `cmd_card` (recebem o `argparse.Namespace`)."""
MODELS = {"ep": "models.ep", "ratings": "models.ratings", "wp_pregame": "models.wp_pregame"}

