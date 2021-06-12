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
from models.policy_value_net_pytorch2 import PolicyValueNet as PytorchPolicyValueNet2 # Pytorch
from models.policy_value_net_pytorch import PolicyValueNet as PytorchPolicyValueNet # Pytorch
from models.policy_value_net_tensorflow import PolicyValueNet as TensorflowPolicyValueNet# Tensorflow
from models.policy_value_net_tensorflow2 import PolicyValueNet as TensorflowPolicyValueNet2# Tensorflow
import pickle
import os
MODEL_CLASSES = {
"numpy":PolicyValueNetNumpy,
"pytorch":PytorchPolicyValueNet,
"pytorch2":PytorchPolicyValueNet2,
"tensorflow":TensorflowPolicyValueNet,
"tensorflow2":TensorflowPolicyValueNet2
}
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--model_type", default="pytorch", type=str,
                    help="Model type selected in the list: " + ", ".join(MODEL_CLASSES.keys()))
parser.add_argument("--board_width", default=9,type=int, help="board_width")
parser.add_argument("--board_height",default=9,type=int,help="board_height")
parser.add_argument("--n_in_row",default=5,type=int,help="n_in_row")
parser.add_argument("--output_dir", default=None, type=str,
                    help="The output directory where the model predictions and checkpoints will be written.")
parser.add_argument("--model_file", default='./best_policy.model', type=str,
                    help="The model_file.")
parser.add_argument("--n_layer_resnet", default=-1, type=int, help="num of simulations for each move.")
parser.add_argument("--enable_gui", default=True, action='store_true',
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
            if isinstance(location, str):  # for python3
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

from UI.gui import GUI
def run():
    n = args.n_in_row
    width, height = args.board_width, args.board_height
    model_file = args.model_file
    # try:
    board = Board(width=width, height=height, n_in_row=n, if_check_forbidden_hands=args.if_check_forbidden_hands)
    game = Game(board, enable_gui=args.enable_gui)
    start_index = 0

    # only load once
    if args.model_type == "numpy":
        policy_param = pickle.load(open(model_file, 'rb'),
                                    encoding='bytes')  # To support python3

        best_policy = MODEL_CLASSES[args.model_type](args, width, height, policy_param)
    else:
        best_policy = MODEL_CLASSES[args.model_type](args, width, height, args.model_file)
    mcts_player = MCTSPlayer(best_policy.policy_value_fn,
                            c_puct=5,
                            n_playout=400)  # set larger n_playout for better performance

    while True:
        start_player = 1 if start_index * 1.0 % 2 == 0 else 0
        
        # human player, input your move in the format: 2,3
        human = Human()

        # set start_player=0 for human first
        winner = game.start_play(human, mcts_player, start_player=start_player, is_shown=1)
        if args.enable_gui:
            game.UI.add_score(winner)
            game.UI.restart_game(False)
        start_index += 1
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

    # except KeyboardInterrupt:
    #     print('\n\rquit')


if __name__ == '__main__':
    run()
