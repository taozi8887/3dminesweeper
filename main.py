from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import random
from flask_session import Session

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change to a strong key in production
app.config['SESSION_TYPE'] = 'filesystem'  # Storing session data on the file system for this example
Session(app)

levels = {
    0: [[4, 4], 2],
    1: [[9, 9], 10],
    2: [[16, 16], 40],
    3: [[30, 16], 99],
}

def initialize_game(level):
    width, height = levels[level][0]
    nm = levels[level][1]
    game_board, mine_locations = create_minesweeper_board(width, height, nm)
    
    session['game_data'] = {
        'width': width,
        'height': height,
        'nm': nm,
        'game_board': game_board,
        'revealed': [],
        'mine_locations': mine_locations,
        'flagged': [],
        'turn': 0,
        'gameover': False,
        'level': level
    }

def create_minesweeper_board(width, height, nm):
    game_board = [[0 for _ in range(width)] for _ in range(height)]
    mine_locations = []
    mine_count = 0

    while mine_count < nm:
        row = random.randint(0, height - 1)
        col = random.randint(0, width - 1)
        if game_board[row][col] != "M":
            game_board[row][col] = "M"
            mine_locations.append((row, col))
            mine_count += 1
            for i in range(max(0, row - 1), min(height, row + 2)):
                for j in range(max(0, col - 1), min(width, col + 2)):
                    if game_board[i][j] != "M":
                        game_board[i][j] += 1
    return game_board, mine_locations

@app.route("/")
def index():
    if 'game_data' not in session:
        initialize_game(0)  # Default to level 0

    game_data = session['game_data']
    html = gethtml(game_data['game_board'], game_data['revealed'])
    for i in (game_data['game_board']):
        print(i)
    return render_template(
        "index.html", 
        css="", 
        html=html, 
        gameover=game_data['gameover'], 
        flagged=len(game_data['flagged']), 
        totalflags=game_data['nm']
    )

@app.route("/cleanreset")
def clean():
    session.pop('game_data', None)
    initialize_game(0)  # Default to level 0
    return redirect(url_for('index'))

@app.route("/reset", methods=["POST"])
def reset():
    level = session['game_data']['level']
    initialize_game(level)
    game_data = session['game_data']
    html = gethtml(game_data['game_board'], game_data['revealed'])
    return jsonify(success=True, html=html)

def reveal_adjacent_squares(row, col, revealed):
    game_data = session['game_data']
    game_board = game_data['game_board']
    if row < 0 or row >= len(game_board) or col < 0 or col >= len(game_board[0]):
        return revealed
    if (row, col) in revealed:
        return revealed
    if (row, col) not in game_data['flagged']:
        revealed.append((row, col))
    if game_board[row][col] != 0:
        return revealed

    reveal_adjacent_squares(row - 1, col, revealed)  # Up
    reveal_adjacent_squares(row + 1, col, revealed)  # Down
    reveal_adjacent_squares(row, col - 1, revealed)  # Left
    reveal_adjacent_squares(row, col + 1, revealed)  # Right

@app.route("/handle_click", methods=["POST"])
def handle_click():
    game_data = session['game_data']
    game_board = game_data['game_board']
    revealed = game_data['revealed']
    turn = game_data['turn']
    
    data = request.get_json()
    row = int(data["row"])
    col = int(data["col"])

    if game_board[row][col] == "M":
        if turn == 0:
            game_board, mine_locations = create_minesweeper_board(game_data['width'], game_data['height'], game_data['nm'])
            session['game_data']['game_board'] = game_board
            session['game_data']['mine_locations'] = mine_locations
            revealed = []
            reveal_adjacent_squares(row, col, revealed)
            session['game_data']['revealed'] = revealed
            return jsonify(success=True, revealed=revealed, game_board=game_board)
        else:
            for r in range(game_data['height']):
                for c in range(game_data['width']):
                    revealed.append((r, c))
            session['game_data']['gameover'] = True
            session['game_data']['revealed'] = revealed
            return jsonify(success=False, gameover=True, revealed=revealed, game_board=game_board)
    else:
        if (row, col) not in revealed:
            session['game_data']['turn'] += 1
        reveal_adjacent_squares(row, col, revealed)
        session['game_data']['revealed'] = revealed
        return jsonify(success=True, revealed=revealed, game_board=game_board)

@app.route("/handle_flag", methods=["POST"])
def handle_flag():
    game_data = session['game_data']
    flagged = game_data['flagged']
    mine_locations = game_data['mine_locations']
    totalflags = game_data['nm']  # Total mines (flags)
    
    data = request.get_json()
    row = int(data["row"])
    col = int(data["col"])
    f = data["flagged"]

    if (row, col) in game_data['revealed']:
        return jsonify(success=False, message="Cannot flag a revealed cell")

    if not f:
        flagged.append((row, col))
        state = True
    else:
        flagged.remove((row, col))
        state = False

    session['game_data']['flagged'] = flagged
    flags = len(set(flagged))  # Number of currently flagged squares

    # Check for win condition (all mines flagged)
    if sorted(flagged) == sorted(mine_locations):
        session['game_data']['gameover'] = True
        for r in range(game_data['height']):
            for c in range(game_data['width']):
                game_data['revealed'].append((r, c))
        session['game_data']['revealed'] = game_data['revealed']
        return jsonify(success=True, win=True, revealed=game_data['revealed'], game_board=game_data['game_board'], nm=totalflags, flags=flags)

    return jsonify(success=True, state=state, nm=totalflags, flags=flags)

def gethtml(li, revealed):
    ctr = 0
    html = ""
    game_data = session['game_data']
    flagged = game_data['flagged']

    def make_square(array):
        height = len(array)
        width = len(array[0]) if height > 0 else 0
        size = max(width, height)
        square_array = [[-1 for _ in range(size)] for _ in range(size)]
        for i in range(height):
            for j in range(width):
                square_array[i][j] = 0
        return square_array

    if len(li) != len(li[0]):
        li = make_square(li)

    while ctr < 2 * len(li) - 1:
        html += '    <div class="row">\n'
        lst = {}
        for i in range(len(li)):
            for j in range(len(li)):
                if i + j == ctr:
                    lst[(i, j)] = li[i][j]
        lst = dict(reversed(list(lst.items())))
        for item in lst:
            row, col = item
            if lst[item] == -1:
                html += f'        <div style="opacity: 0;visibility: hidden;" class="surface"></div>\n'
            elif item in flagged:
                html += f'        <div class="surface flagged" data-row="{row}" data-col="{col}"><span class="surfacetext"></span></div>\n'
            elif item in revealed:
                a = 'g' if lst[item] == 1 else 'y' if lst[item] == 2 else 'r' if lst[item] > 2 else ''
                if lst[item] == 0:
                    html += f'        <div class="surface empty revealed" data-row="{row}" data-col="{col}"><span class="surfacetext"></span></div>\n'
                else:
                    html += f'        <div class="surface revealed {a}" data-row="{row}" data-col="{col}"><span class="surfacetext">{lst[item]}</span></div>\n'
            else:
                html += f'        <div class="surface" data-row="{row}" data-col="{col}"><span class="surfacetext"></span></div>\n'
        html += "    </div>\n"
        ctr += 1
    return html

@app.route("/set_level", methods=["POST"])
def set_level():
    data = request.get_json()
    level = data["level"]

    # Update session with the new level and game parameters
    session['game_data'] = {
        'level': level,
        'width': levels[level][0][0],
        'height': levels[level][0][1],
        'nm': levels[level][1],
        'revealed': [],
        'flagged': [],
        'mine_locations': [],
        'turn': 0,
        'gameover': False
    }
    
    game_data = session['game_data']
    game_data['game_board'], game_data['mine_locations'] = create_minesweeper_board(game_data['width'], game_data['height'], game_data['nm'])
    session['game_data'] = game_data

    # Generate the new HTML for the updated board
    html = gethtml(game_data['game_board'], game_data['revealed'])

    return jsonify(success=True, html=html, flags=len(set(game_data['flagged'])), nm=game_data['nm'])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
