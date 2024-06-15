import socket
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox
import pickle
import chess
import sys

class ChessClient(tk.Tk):
    def __init__(self, host='localhost', port=5555):
        super().__init__()
        self.title("Chess Game")
        self.geometry("600x600")
        
        self.board = chess.Board()
        self.canvas = tk.Canvas(self, width=600, height=600, bg="#F0D9B5")
        self.canvas.pack()
        self.is_flipped = False  # Indicates if the board is flipped
        
        self.draw_board()
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        
        self.player_id = None
        self.selected_square = None
        self.my_turn = False  # Indicates if it is this client's turn
        
        self.socket_thread = threading.Thread(target=self.listen_for_server)
        self.socket_thread.start()
        
        self.bind("<Button-1>", self.click_square)
        
        # Display the initial message
        self.after(100, lambda: messagebox.showinfo("Game Start", "White will move first."))
    
    def draw_board(self):
        self.squares = []
        for i in range(8):
            row = []
            for j in range(8):
                color = "#F0D9B5" if (i + j) % 2 == 0 else "#B58863"
                square = self.canvas.create_rectangle(j * 75, i * 75, (j + 1) * 75, (i + 1) * 75, fill=color, outline="")
                row.append(square)
            self.squares.append(row)
        self.place_pieces()
    
    def place_pieces(self):
        self.canvas.delete("piece")
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                if self.is_flipped:
                    x = ((7 - chess.square_file(square)) * 75) + 37
                    y = (chess.square_rank(square) * 75) + 37
                else:
                    x = (chess.square_file(square) * 75) + 37
                    y = ((7 - chess.square_rank(square)) * 75) + 37
                self.canvas.create_text(x, y, text=self.get_piece_symbol(piece.symbol()), font=("Arial", 36), fill="#000", tags="piece")
    
    def get_piece_symbol(self, piece):
        symbols = {
            'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
            'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
        }
        return symbols.get(piece, piece)
    
    def click_square(self, event):
        if self.is_flipped:
            col = 7 - (event.x // 75)
            row = event.y // 75
        else:
            col = event.x // 75
            row = 7 - (event.y // 75)

        if self.my_turn:
            if self.selected_square is not None:
                move = chess.Move.from_uci(f"{chess.square_name(self.selected_square)}{chess.square_name(chess.square(col, row))}")
                
                # Handle pawn promotion
                if self.board.piece_at(self.selected_square).piece_type == chess.PAWN and (row == 0 or row == 7):
                    move.promotion = chess.QUEEN
                
                if move in self.board.legal_moves:
                    self.send_move(move)
                    self.selected_square = None
                else:
                    messagebox.showinfo("Invalid Move", "Invalid Move!")
                    self.selected_square = None
            else:
                piece = self.board.piece_at(chess.square(col, row))
                if piece and (piece.color == (chess.WHITE if self.player_id == 0 else chess.BLACK)):
                    self.selected_square = chess.square(col, row)
                    self.highlight_square(row, col)
                    self.after(3000, lambda: self.unhighlight_square(row, col))
    
    def highlight_square(self, row, col):
        color = "#ADD8E6"
        if self.is_flipped:
            row = 7 - row
            col = 7 - col
        self.canvas.itemconfig(self.squares[7 - row][col], fill=color)
    
    def unhighlight_square(self, row, col):
        if self.is_flipped:
            row = 7 - row
            col = 7 - col
        original_color = "#F0D9B5" if (7 - row + col) % 2 == 0 else "#B58863"
        self.canvas.itemconfig(self.squares[7 - row][col], fill=original_color)
    
    def listen_for_server(self):
        while True:
            try:
                data = pickle.loads(self.socket.recv(4096))
                if "player_id" in data:
                    self.player_id = data["player_id"]
                    # Set initial board orientation based on player ID
                    self.is_flipped = (self.player_id == 1)
                    self.place_pieces()
                if "board" in data:
                    self.update_board(data["board"], data["turn"])
                if "board_status" in data:
                    self.show_game_status(data["board_status"])
                if "reset_board" in data and data["reset_board"]:
                    self.reset_game()  # Reset the game upon receiving the reset signal
            except Exception as e:
                print(f"Error: {e}")
                break
    
    def update_board(self, board_fen, turn):
        self.board.set_fen(board_fen)
        self.my_turn = (turn == (chess.WHITE if self.player_id == 0 else chess.BLACK))
        self.selected_square = None
        self.place_pieces()
    
    def send_move(self, move):
        self.socket.send(pickle.dumps({"move": move.uci()}))
    
    def show_game_status(self, status):
        if status == "check":
            messagebox.showinfo("Check", "Check!")
        elif status == "checkmate":
            messagebox.showinfo("Game Over", f"Checkmate!!")
            self.quit_game()  # Terminate the game upon checkmate
        elif status == "stalemate":
            messagebox.showinfo("Game Over", "Stalemate! The game is a draw.")
            self.quit_game()  # Terminate the game upon stalemate
    
    def reset_game(self):
        self.board.reset()  # Reset the internal board representation
        self.my_turn = False
        self.selected_square = None
        self.place_pieces()
    
    def quit_game(self):
        self.socket.close()  # Close the socket connection
        self.quit()  # Terminate the main Tkinter loop
        self.destroy()  # Destroy the Tkinter window
        sys.exit(0)  # Terminate the program

def get_server_ip():
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    ip = simpledialog.askstring("Server IP", "Enter the server IP address:", initialvalue="localhost")
    root.destroy()  # Destroy the root window after input
    return ip

def main():
    ip = get_server_ip()
    if ip:
        game = ChessClient(host=ip)
        game.mainloop()

if __name__ == "__main__":
    main()