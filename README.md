## AlphaZero-Gomoku
Fork from [junxiaosong/AlphaZero_Gomoku](https://github.com/junxiaosong/AlphaZero_Gomoku)

### Requirements
To play with the trained AI models, only need:
- Python == 3.6
- tensorflow-gpu==1.15.0

### Getting Started
To play with provided models, run the following script from the directory.
Use TensorFlow:
```
python human_play.py --model_type tensorflow --board_width 9 --board_height 9 --n_in_row 5 --model_file best_model_tf\best_policy.model
```
You may modify human_play.py to try different provided models or the pure MCTS.

To train the AI model from scratch, with Theano and Lasagne, directly run:
Use TensorFlow:
```
python train.py --model_type tensorflow --board_width 9 --board_height 9 --n_in_row 5 --output_dir output --check_freq 200 --game_batch_num 4000 --ef_for_eight 4 --disable_equi_logic
```
Use TensorFlow with Resnet:
```
python train.py --model_type tensorflow2 --board_width 9 --board_height 9 --n_in_row 5 --output_dir output --check_freq 200 --game_batch_num 4000 --ef_for_eight 4 --disable_equi_logic --n_layer_resnet 4
```

Compare models:
```
python evaluate_play.py --model_type1 tensorflow --model_type2 tensorflow --model_file1 best_model_tf\best_policy.model --model_file2 best_model_tf\best_policy.model --round_num 1 --enable_gui
```