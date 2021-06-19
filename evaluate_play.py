# -*- coding: utf-8 -*-
"""
human VS AI models
Input your move in the format: 2,3

@author: Junxiao Song
"""

from __future__ import print_function
from game import Board, Game
from models.mcts_alphaZero import MCTSPlayer
from models.policy_value_net_numpy import PolicyValueNetNumpy
#from models.policy_value_net_pytorch import PolicyValueNet as PytorchPolicyValueNet # Pytorch
from models.policy_value_net_tensorflow import PolicyValueNet as TensorflowPolicyValueNet# Tensorflow
#from models.policy_value_net_pytorch2 import PolicyValueNet as PytorchPolicyValueNet2 # Pytorch
from models.policy_value_net_tensorflow2 import PolicyValueNet as TensorflowPolicyValueNet2# Tensorflow
import pickle
import random
import os
import json
import os

MODEL_CLASSES = {
"numpy":PolicyValueNetNumpy,
#"pytorch":PytorchPolicyValueNet,
#"pytorch2":PytorchPolicyValueNet2,
"tensorflow":TensorflowPolicyValueNet,
"tensorflow2":TensorflowPolicyValueNet2,
}
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--model_type1", default="pytorch", type=str,
                    help="Model type selected in the list: " + ", ".join(MODEL_CLASSES.keys()))
parser.add_argument("--model_type2", default="pytorch", type=str,
                    help="Model type selected in the list: " + ", ".join(MODEL_CLASSES.keys()))
parser.add_argument("--board_width", default=9,type=int, help="board_width")
parser.add_argument("--board_height",default=9,type=int,help="board_height")
parser.add_argument("--n_in_row",default=5,type=int,help="n_in_row")
parser.add_argument("--output_dir", default="./", type=str,
                    help="The output directory where the model predictions and checkpoints will be written.")
parser.add_argument("--model_file1", default='./best_policy.model', type=str,
                    help="The model_file.")
parser.add_argument("--model_file2", default='./best_policy.model', type=str,
                    help="The model_file.")
parser.add_argument("--round_num",default=2,type=int,help="round number")
parser.add_argument("--n_playout",default=400,type=int,help="n_playout")
parser.add_argument("--n_layer_resnet", default=-1, type=int, help="num of simulations for each move.")
parser.add_argument("--enable_gui", action='store_true',
                    help="enable_gui")
parser.add_argument("--if_check_forbidden_hands", action='store_true',
                    help="if check forbidden hands, default false")


args, _ = parser.parse_known_args()
print("Print the args:")
for key, value in sorted(args.__dict__.items()):
    print("{} = {}".format(key, value))

class Human(object):
    """
    human player
    """

    def __init__(self):
        self.player = None

    def set_player_ind(self, p):
        self.player = p

    def get_action(self, board):
        try:
            location = input("Your move: ")
            if isinstance(location, str):  # for python3
                location = [int(n, 10) for n in location.split(",")]
            move = board.location_to_move(location)
        except Exception as e:
            move = -1
        if move == -1 or move not in board.availables:
            print("invalid move")
            move = self.get_action(board)
        return move

    def __str__(self):
        return "Human {}".format(self.player)
class Human(object):
    """
    human player
    """

    def __init__(self):
        self.player = None

    def set_player_ind(self, p):
        self.player = p

    # def get_action(self, board):
    #     try:
    #         location = input("Your move: ")
    #         if isinstance(location, str):  # for python3
    #             location = [int(n, 10) for n in location.split(",")]
    #         move = board.location_to_move(location)
    #     except Exception as e:
    #         move = -1
    #     if move == -1 or move not in board.availables:
    #         print("invalid move")
    #         move = self.get_action(board)
    #     return move
    #
    # def __str__(self):
    #     return "Human {}".format(self.player)
    def get_action(self, board, UI=None):
        try:
            # location = input("Your move: ")
            inp = UI.get_input()
            location = UI.move_2_loc(inp[1])
            print(location)
            if isinstance(location, str):  # for python3v
                location = [int(n, 10) for n in location.split(",")]
            move = board.location_to_move(location)

        except Exception as e:
            move = -1
        if move == -1 or move not in board.availables:
            print("invalid move")
            move = self.get_action(board, UI)

        return move

    def __str__(self):
        return "Human {}".format(self.player)

def get_mcts_player(model_type, model_file, width, height):
    if model_type == "numpy":
        policy_param = pickle.load(open(model_file, 'rb'),
                                   encoding='bytes')  # To support python3

        best_policy = MODEL_CLASSES[model_type](args, width, height, policy_param)
    else:
        best_policy = MODEL_CLASSES[model_type](args, width, height, model_file=model_file)
    mcts_player = MCTSPlayer(best_policy.policy_value_fn,
                             c_puct=5,
                             n_playout=args.n_playout)  # set larger n_playout for better performance
    return mcts_player
from UI.gui import GUI
def run():
    n = args.n_in_row
    width, height = args.board_width, args.board_height
    board = Board(width=width, height=height, n_in_row=n, if_check_forbidden_hands=args.if_check_forbidden_hands)
    game = Game(board, enable_gui=args.enable_gui)
    mcts1 = get_mcts_player(args.model_type1, args.model_file1, width, height)
    mcts2 = get_mcts_player(args.model_type2, args.model_file2, width, height)
    # mcts1 = Human()
    # mcts2 = Human()
    winner_dict = dict()
    while True:
        if args.enable_gui:
            game.UI.reset_score()
        for i in range(0, args.round_num):
            start_player = 1 if i * 1.0 % 2 == 0 else 0
            print("start player")
            print(start_player)
            winner = game.start_play(mcts1, mcts2, start_player=start_player, is_shown=1)
            if winner not in winner_dict:
                winner_dict[winner] = 0
            winner_dict[winner] += 1
            if args.enable_gui:
                game.UI.add_score(winner)
                game.UI.restart_game(False)
        if args.enable_gui:
            inp = game.UI.get_input()
            if inp[0] == 'RestartGame':
                game.UI.restart_game()

            elif inp[0] == 'ResetScore':
                game.UI.reset_score()
                continue

            elif inp[0] == 'quit':
                exit()
            elif inp[0] == 'SwitchPlayer':
                game.UI.restart_game(False)
                game.UI.reset_score()
            else:
                continue

    print("output winner dict to {}".format(os.path.join(args.output_dir, "winner_dict.tsv")))
    with open(os.path.join(args.output_dir, "winner_dict.tsv"), 'w', encoding='utf8') as fout:
        fout.write(json.dumps(winner_dict))
    print("winner dict:")
    print(winner_dict)

if __name__ == '__main__':
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    run()
