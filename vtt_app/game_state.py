from typing import Any


class GameState:
    def __init__(self) -> None:
        self._game_state = {
            'map': {'width': 20, 'height': 20, 'tokens': []},
            'players': {}
        }

    def get_map(self) -> dict[str, Any]:
        return self._game_state['map']

    def add_token(self, token: dict[str, Any]) -> dict[str, Any]:
        self._game_state['map']['tokens'].append(token)
        return token

    def update_token(self, token_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        for token in self._game_state['map']['tokens']:
            if token.get('id') == token_id:
                token.update(data)
                return token
        return None

    def delete_token(self, token_id: str) -> None:
        self._game_state['map']['tokens'] = [t for t in self._game_state['map']['tokens'] if t.get('id') != token_id]
