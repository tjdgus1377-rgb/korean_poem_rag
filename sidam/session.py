from copy import deepcopy


def history(state, poem_id):
    return state.setdefault("messages_by_poem_id", {}).setdefault(poem_id, [])


def add_message(state, poem_id, message):
    history(state, poem_id).append(deepcopy(message))


def validate_quote(text, quote):
    return bool(quote.strip()) and "".join(quote.split()) in "".join(text.split())
