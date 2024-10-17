from flask import Flask, render_template, request, jsonify
import random

app = Flask(__name__)

width, height = 3,3
revealed = []
mine_locations = []
nm = 1
flagged = []
turn = 0
gameover = False


def create_minesweeper_board(width, height, nm):
    # Step 1: Initialize the board with empty cells (0 means no adjacent mines)
    ml = []
    game_board = [[0 for _ in range(width)] for _ in range(height)]

    # Step 2: Place mines randomly on the board
    mine_count = 0
    while mine_count < nm:
        # Generate random coordinates for the mine
        row = random.randint(0, height - 1)
        col = random.randint(0, width - 1)

        # Only place a mine if the cell is not already a mine
        if game_board[row][col] != "M":
            game_board[row][col] = "M"
            ml.append((row, col))
            mine_count += 1

            # Step 3: Update adjacent cells' mine count
            for i in range(max(0, row - 1), min(height, row + 2)):
                for j in range(max(0, col - 1), min(width, col + 2)):
                    if game_board[i][j] != "M":  # Don't update the mine itself
                        game_board[i][j] += 1

    return game_board, ml


@app.route("/reset", methods=["POST"])
def reset():
    global game_board, revealed, turn, gameover, flagged, mine_locations  # Ensure these are accessible globally
    revealed = []  # Reset the revealed cells
    turn = 0
    flagged = []
    gameover = False
    game_board, mine_locations = create_minesweeper_board(width, height, nm)  # Recreate the game board

    css = ""
    html = gethtml(game_board, revealed)  # Get the new HTML representation
    return jsonify(success=True, html=html)  # Return the new HTML to the frontend


def gethtml(li, revealed):
    ctr = 0
    html = ""

    def make_square(array):
        # Get the dimensions of the original rectangle
        height = len(array)
        width = len(array[0]) if height > 0 else 0

        # Determine the size of the square
        size = max(width, height)

        # Create a new square array initialized with -1
        square_array = [[-1 for _ in range(size)] for _ in range(size)]

        # Fill the square array with 0s from the original rectangle
        for i in range(height):
            for j in range(width):
                square_array[i][j] = 0

        return square_array

    if len(li) != len(li[0]):
        li = make_square(li)
    while ctr < 2 * (len(li)) - 1:
        html += '    <div class="row">\n'
        lst = {}

        # Iterate over the height (rows)
        for i in range(len(li)):

            # Iterate over the width (columns)
            for j in range(len(li)):

                # Diagonal elements condition
                if i + j == ctr:
                    lst[(i, j)] = li[i][j]

        # Reverse the list for diagonal printing and output HTML divs
        lst = dict(reversed(list(lst.items())))
        for item in lst:
            row, col = item
            if lst[item] == -1:
                html += f'        <div style="opacity: 0;visibility: hidden;" class="surface"></div>\n'
            elif item in revealed:
                a = 'g' if lst[item] == 1 else 'y' if lst[item] == 2 else 'r' if lst[item] > 2 else ''
                print(a)
                if lst[item] == 0:
                    html += f'        <div class="surface empty revealed" data-row="{row}" data-col="{col}"><span class="surfacetext"></span></div>\n'
                else:
                    html += f'        <div class="surface revealed {a}" data-row="{row}" data-col="{col}"><span class="surfacetext">{lst[item]}</span></div>\n'
            else:
                html += f'        <div class="surface" data-row="{row}" data-col="{col}"><span class="surfacetext"></span></div>\n'

        html += "    </div>\n"
        ctr += 1
    return html


@app.route("/")
def index():
    global game_board, revealed, turn, gameover, flagged, mine_locations  # Ensure these are accessible globally
    revealed = []  # Reset the revealed cells
    flagged = []
    turn = 0
    gameover = False
    css = ""
    game_board, mine_locations = create_minesweeper_board(width, height, nm)

    for i in game_board:
        print(i)

    html = gethtml(game_board, revealed)
    return render_template("index.html", css=css, html=html, gameover=gameover)


def reveal_adjacent_squares(row, col, revealed):
    # Check boundaries of the board
    if row < 0 or row >= len(game_board) or col < 0 or col >= len(game_board[0]):
        return revealed

    # If the cell is already revealed, do nothing
    if (row, col) in revealed:
        return revealed

    # Reveal the current cell
    revealed.append((row, col))

    # If the cell is not a 0 (empty), stop recursion
    if game_board[row][col] != 0:
        return revealed

    # Reveal neighbors in each direction: up, down, left, right
    # Move Up (row - 1, same col)
    if row - 1 >= 0 and (row - 1, col) not in revealed:
        reveal_adjacent_squares(row - 1, col, revealed)

    # Move Down (row + 1, same col)
    if row + 1 < len(game_board) and (row + 1, col) not in revealed:
        reveal_adjacent_squares(row + 1, col, revealed)

    # Move Left (same row, col - 1)
    if col - 1 >= 0 and (row, col - 1) not in revealed:
        reveal_adjacent_squares(row, col - 1, revealed)

    # Move Right (same row, col + 1)
    if col + 1 < len(game_board[0]) and (row, col + 1) not in revealed:
        reveal_adjacent_squares(row, col + 1, revealed)


@app.route("/handle_click", methods=["POST"])
def handle_click():
    global revealed, turn, game_board
    data = request.get_json()
    row = int(data["row"])
    col = int(data["col"])

    # Check if the clicked cell is a mine
    if game_board[row][col] == "M":
        if turn == 0:
            game_board = create_minesweeper_board(width, height, nm)
            revealed = []
            reveal_adjacent_squares(row, col, revealed)
            return jsonify(success=True, revealed=revealed, game_board=game_board)
        else:
            for r in range(height):
                for c in range(width):
                    revealed.append((r, c))  # Add all cells to the revealed list
            gameover = True
            return jsonify(
                success=False, gameover=True, revealed=revealed, game_board=game_board
            )  # Example response for a mine
    else:
        if (row, col) not in revealed:
            turn += 1
        reveal_adjacent_squares(row, col, revealed)

        # Return the revealed board (for simplicity, sending only the revealed cells)
        return jsonify(success=True, revealed=revealed, game_board=game_board)


@app.route("/handle_flag", methods=["POST"])
def handle_flag():
    data = request.get_json()
    row = int(data["row"])
    col = int(data["col"])
    f = data["flagged"]  # True if flagging, False if unflagging


    # Check if the cell is valid for flagging
    if (row, col) in revealed:
        return jsonify(success=False, message="Cannot flag a revealed cell")

    # Update the flagged state of the cell
    if f:
        flagged.append((row, col))  # Add the cell to the flagged set
    else:
        flagged.remove((row, col))  # Remove the cell from the flagged set

    if sorted(flagged) == sorted(mine_locations):
        gameover = True
        for r in range(height):
                for c in range(width):
                    revealed.append((r, c))  # Add all cells to the revealed list
        return jsonify(success=True, win=True, revealed=revealed, game_board=game_board)

    return jsonify(success=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
