# -*- coding: utf-8 -*-
"""
An implementation of the training pipeline of AlphaZero for Gomoku

@author: Junxiao Song
"""

from __future__ import print_function
import random
import numpy as np
from tensorboardX import SummaryWriter
from collections import defaultdict, deque
from game import Board, Game
from models.mcts_pure import MCTSPlayer as MCTS_Pure
from models.mcts_alphaZero import MCTSPlayer
from models.policy_value_net_pytorch import PolicyValueNet as PytorchPolicyValueNet # Pytorch
from models.policy_value_net_pytorch2 import PolicyValueNet as PytorchPolicyValueNet2 # Pytorch

from models.policy_value_net_tensorflow import PolicyValueNet as TensorflowPolicyValueNet# Tensorflow
from models.policy_value_net_tensorflow2 import PolicyValueNet as TensorflowPolicyValueNet2# Tensorflow
import os
MODEL_CLASSES = {
"pytorch":PytorchPolicyValueNet,
"pytorch2":PytorchPolicyValueNet2,
"tensorflow":TensorflowPolicyValueNet,
"tensorflow2":TensorflowPolicyValueNet2
}
#from models.policy_value_net_keras import PolicyValueNet as KerasPolicyValueNet# Keras
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--data_dir", default=None, type=str,
                    help="The input data dir. Should contain the .tsv files (or other data files) for the task.")
parser.add_argument("--model_type", default="pytorch", type=str,
                    help="Model type selected in the list: " + ", ".join(MODEL_CLASSES.keys()))
parser.add_argument("--board_width", default=9,type=int, help="board_width")
parser.add_argument("--board_height",default=9,type=int,help="board_height")
parser.add_argument("--n_in_row",default=5,type=int,help="n_in_row")
parser.add_argument("--learn_rate", default=2e-3, type=float,help="The initial learning rate for Adam.")
parser.add_argument("--lr_multiplier", default=1.0, type=float,help="lr_multiplier.")
parser.add_argument("--temp", default=1.0, type=float,help="temp.")
parser.add_argument("--n_playout", default=400, type=int,help="num of simulations for each move.")
parser.add_argument("--c_puct", default=5, type=int,help="the temperature param.")
parser.add_argument("--buffer_size", default=10000, type=int,help="buffer_size.")
parser.add_argument("--batch_size", default=512, type=int,help="batch_size.")
parser.add_argument("--play_batch_size", default=1, type=int,help="play_batch_size.")
parser.add_argument("--epochs", default=5, type=int,help="epochs.")
parser.add_argument("--kl_targ", default=0.02, type=float,help="kl_targ.")
parser.add_argument("--check_freq", default=50, type=int,help="check_freq.")
parser.add_argument("--game_batch_num", default=1500, type=int,help="game_batch_num.")
parser.add_argument("--best_win_ratio", default=0.0, type=int,help="best_win_ratio.")
parser.add_argument("--pure_mcts_playout_num", default=1000, type=int,help="pure_mcts_playout_num.")
parser.add_argument("--output_dir", default="./", type=str,
                    help="The output directory where the model predictions and checkpoints will be written.")
parser.add_argument("--continue_train", action='store_true', help="whether to continue_train")
parser.add_argument("--model_file", default=None, type=str,
                    help="The model_file.")
parser.add_argument("--n_layer_resnet", default=-1, type=int, help="num of simulations for each move.")
parser.add_argument("--ef_for_eight", default=-1, type=int,
                    help="efficient for eight connected region, <=0 to disable it")
parser.add_argument("--enable_random_logic", action='store_true',
                    help="enable random movement logic")
parser.add_argument("--disable_equi_logic", action='store_true',
                    help="disable_equi_logic")
parser.add_argument("--if_check_forbidden_hands", action='store_true',
                    help="if check forbidden hands, default false")

args, _ = parser.parse_known_args()
print("Print the args:")
for key, value in sorted(args.__dict__.items()):
    print("{} = {}".format(key, value))

tb_writer = SummaryWriter(args.output_dir)

class TrainPipeline():
    def __init__(self, init_model=None):
        # params of the board and the game
        self.board_width = args.board_width
        self.board_height = args.board_height
        self.n_in_row = args.n_in_row
        self.board = Board(width=self.board_width,
                           height=self.board_height,
                           n_in_row=self.n_in_row,
                           ef_for_eight=args.ef_for_eight,
                           if_check_forbidden_hands=args.if_check_forbidden_hands)
        self.game = Game(self.board)
        # training params
        self.learn_rate = args.learn_rate
        self.lr_multiplier = args.lr_multiplier  # adaptively adjust the learning rate based on KL
        self.temp = args.temp  # the temperature param
        self.n_playout = args.n_playout  # num of simulations for each move
        self.c_puct = args.c_puct
        self.buffer_size = args.buffer_size
        self.batch_size = args.batch_size  # mini-batch size for training
        self.data_buffer = deque(maxlen=self.buffer_size)
        self.play_batch_size = args.play_batch_size
        self.epochs = args.epochs  # num of train_steps for each update
        self.kl_targ = args.kl_targ
        self.check_freq = args.check_freq
        self.game_batch_num = args.game_batch_num
        self.best_win_ratio = args.best_win_ratio
        # num of simulations used for the pure mcts, which is used as
        # the opponent to evaluate the trained policy
        self.pure_mcts_playout_num = args.pure_mcts_playout_num
        if init_model:
            # start training from an initial policy-value net
            print("start training from an initial policy-value net")
            self.policy_value_net = MODEL_CLASSES[args.model_type](args, self.board_width,
                                                   self.board_height,
                                                   training=True,
                                                   model_file=init_model)
        else:
            # start training from a new policy-value net
            print("start training from a new policy-value net")
            self.policy_value_net = MODEL_CLASSES[args.model_type](args, self.board_width,
                                                   self.board_height,
                                                   training=True)
        self.mcts_player = MCTSPlayer(self.policy_value_net.policy_value_fn,
                                      c_puct=self.c_puct,
                                      n_playout=self.n_playout,
                                      is_selfplay=1,
                                      ef_for_eight=args.ef_for_eight)
        self.logs = {}

    def get_equi_data(self, play_data):
        """augment the data set by rotation and flipping
        play_data: [(state, mcts_prob, winner_z), ..., ...]
        """
        extend_data = []
        for state, mcts_porb, winner in play_data:
            for i in [1, 2, 3, 4]:
                # rotate counterclockwise
                equi_state = np.array([np.rot90(s, i) for s in state])
                equi_mcts_prob = np.rot90(np.flipud(
                    mcts_porb.reshape(self.board_height, self.board_width)), i)
                extend_data.append((equi_state,
                                    np.flipud(equi_mcts_prob).flatten(),
                                    winner))
                # flip horizontally
                equi_state = np.array([np.fliplr(s) for s in equi_state])
                equi_mcts_prob = np.fliplr(equi_mcts_prob)
                extend_data.append((equi_state,
                                    np.flipud(equi_mcts_prob).flatten(),
                                    winner))
        return extend_data

    def collect_selfplay_data(self, n_games=1):
        """collect self-play data for training"""
        print("~~~~~~~~~~~~~~~ start self play ~~~~~~~~~~~~~~~~~~~~~~")
        for i in range(n_games):
            winner, play_data = self.game.start_self_play(self.mcts_player,
                                                          temp=self.temp)
            play_data = list(play_data)[:]
            self.episode_len = len(play_data)
            # augment the data
            if not args.disable_equi_logic:
                play_data = self.get_equi_data(play_data)
            self.data_buffer.extend(play_data)
    def collect_selfplay_data_random(self, n_games=1):
        """collect self-play data for training"""
        print("~~~~~~~~~~~~~~~ start self play ~~~~~~~~~~~~~~~~~~~~~~")
        for i in range(n_games):
            winner, play_data = self.game.start_self_play_random(self.mcts_player,
                                                          temp=self.temp)
            play_data = list(play_data)[:]
            self.episode_len = len(play_data)
            # augment the data
            if not args.disable_equi_logic:
                play_data = self.get_equi_data(play_data)
            self.data_buffer.extend(play_data)


    def policy_update(self, step_index):
        logs = {}
        """update the policy-value net"""
        mini_batch = random.sample(self.data_buffer, self.batch_size)
        state_batch = [data[0] for data in mini_batch]
        mcts_probs_batch = [data[1] for data in mini_batch]
        winner_batch = [data[2] for data in mini_batch]
        old_probs, old_v = self.policy_value_net.policy_value(state_batch)
        for i in range(self.epochs):
            loss, entropy = self.policy_value_net.train_step(
                    state_batch,
                    mcts_probs_batch,
                    winner_batch,
                    self.learn_rate*self.lr_multiplier)
            new_probs, new_v = self.policy_value_net.policy_value(state_batch)
            kl = np.mean(np.sum(old_probs * (
                    np.log(old_probs + 1e-10) - np.log(new_probs + 1e-10)),
                    axis=1)
            )
            if kl > self.kl_targ * 4:  # early stopping if D_KL diverges badly
                break
        # adaptively adjust the learning rate
        if kl > self.kl_targ * 2 and self.lr_multiplier > 0.1:
            self.lr_multiplier /= 1.5
        elif kl < self.kl_targ / 2 and self.lr_multiplier < 10:
            self.lr_multiplier *= 1.5

        explained_var_old = (1 -
                             np.var(np.array(winner_batch) - old_v.flatten()) /
                             np.var(np.array(winner_batch)))
        explained_var_new = (1 -
                             np.var(np.array(winner_batch) - new_v.flatten()) /
                             np.var(np.array(winner_batch)))
        result = dict()
        result["kl"] = kl
        result["lr_multiplier"] = self.lr_multiplier
        result["loss"] = loss
        result["entropy"] = entropy
        result["explained_var_old"] = explained_var_old
        result["explained_var_new"] = explained_var_new

        for key, value in result.items():
            eval_key = 'train_{}'.format(key)
            logs[eval_key] = value
        for key, value in logs.items():
            tb_writer.add_scalar(key, value, step_index)

        print(("kl:{:.5f},"
               "lr_multiplier:{:.3f},"
               "loss:{},"
               "entropy:{},"
               "explained_var_old:{:.3f},"
               "explained_var_new:{:.3f}"
               ).format(kl,
                        self.lr_multiplier,
                        loss,
                        entropy,
                        explained_var_old,
                        explained_var_new))
        return loss, entropy

    def policy_evaluate(self,step_index, n_games=6):
        """
        Evaluate the trained policy by playing against the pure MCTS player
        Note: this is only for monitoring the progress of training
        """
        logs = dict()
        current_mcts_player = MCTSPlayer(self.policy_value_net.policy_value_fn,
                                         c_puct=self.c_puct,
                                         n_playout=self.n_playout,
                                         ef_for_eight=args.ef_for_eight)
        pure_mcts_player = MCTS_Pure(c_puct=5,
                                     n_playout=self.pure_mcts_playout_num)
        win_cnt = defaultdict(int)
        for i in range(n_games):
            winner = self.game.start_play(current_mcts_player,
                                          pure_mcts_player,
                                          start_player=i % 2,
                                          is_shown=0)
            win_cnt[winner] += 1
        win_ratio = 1.0*(win_cnt[1] + 0.5*win_cnt[-1]) / n_games
        print("num_playouts:{}, win: {}, lose: {}, tie:{}".format(
                self.pure_mcts_playout_num,
                win_cnt[1], win_cnt[2], win_cnt[-1]))
        result = dict()
        result["num_playouts"] = self.pure_mcts_playout_num
        result["win"] = win_cnt[1]
        result["lose"] = win_cnt[2]
        result["tie"] = win_cnt[-1]

        for key, value in result.items():
            eval_key = 'eval_{}'.format(key)
            logs[eval_key] = value
        for key, value in logs.items():
            tb_writer.add_scalar(key, value, step_index)

        return win_ratio

    def run(self):
        """run the training pipeline"""
        try:
            for i in range(self.game_batch_num):
                if args.enable_random_logic:
                    self.collect_selfplay_data_random(self.play_batch_size)
                else:
                    if i < 1000:
                        self.collect_selfplay_data(self.play_batch_size)
                    else:
                        self.collect_selfplay_data_random(self.play_batch_size)

                print("batch i:{}, episode_len:{}".format(
                        i+1, self.episode_len))
                if len(self.data_buffer) > self.batch_size:
                    loss, entropy = self.policy_update(i)
                # check the performance of the current model,
                # and save the model params
                if (i+1) % self.check_freq == 0:
                    print("current self-play batch: {}".format(i+1))
                    win_ratio = self.policy_evaluate(i, n_games=6)
                    self.policy_value_net.save_model(os.path.join(args.output_dir, 'current_policy.model'))
                    if win_ratio > self.best_win_ratio:
                        print("New best policy!!!!!!!!")
                        self.best_win_ratio = win_ratio
                        # update the best_policy
                        self.policy_value_net.save_model(os.path.join(args.output_dir, 'best_policy.model'))
                        if (self.best_win_ratio == 1.0 and
                                self.pure_mcts_playout_num < 5000):
                            self.pure_mcts_playout_num += 1000
                            self.best_win_ratio = 0.0
        except KeyboardInterrupt:
            print('\n\rquit')


if __name__ == '__main__':
    if args.continue_train and (args.output_dir is not None and os.path.isfile(os.path.join(args.output_dir,"current_policy.model"))):
        checkpoint = os.path.join(args.output_dir,"current_policy.model")
        training_pipeline = TrainPipeline(checkpoint)
    else:
        training_pipeline = TrainPipeline(args.model_file)
    training_pipeline.run()
