import numpy as np
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from matplotlib import pyplot as plt
from tensorflow import keras
from keras.models import Sequential
from keras.layers import Dense, Dropout
from keras.losses import SparseCategoricalCrossentropy
from keras.losses import MeanSquaredError

# Custom Modules
import utils


# Tensorflow and SVM Functions

def neuron_permutor(n_hidden: int, max_neuron='auto', min_neuron=32) -> list:
    """Return the permutation of number of nuerons for a neural network.

    Args:
        n_hidden (int): Number of hidden layers.
        max_neuron (int, optional): Max number of neurons. Defaults to 256.
        min_neuron (int, optional): Min number of neurons. Defaults to 32.

    Returns:
        list: A list of permutation.
    """
    if n_hidden < 1:
        print("Number of hidden layer must >= 1.")
        exit()

    if max_neuron == 'auto':
        power = np.log2(32) + n_hidden - 1
        max_neuron = int(2 ** power)

    initial = [max_neuron for _ in range(n_hidden)]

    result = [initial.copy()]
    pointer = n_hidden - 1
    prev_lowest = min_neuron
    cur_combination = initial.copy()
    while pointer >= 0:
        cur_neuron = cur_combination[pointer]

        while cur_neuron > prev_lowest:
            cur_combination[pointer] = int(cur_neuron / 2)
            cur_neuron = cur_combination[pointer]

            result.append(cur_combination.copy())

        if cur_neuron <= prev_lowest:
            prev_lowest *= 2

        pointer -= 1

    return result


def KFold_training(
    n_splits: int,
    x_data: np.ndarray,
    y_data: np.ndarray,
    neurons_layout: list,
    activation: str,
    selected_bands: list,
    learning_rate: int,
    batch_size: int,
    valid_ratio: float,
    n_epochs: int,
    callbacks: list,
    save_path: str
):
    """Operate K-Fold training.

    Args:
        n_splits (int): Number of K.
        x_data (np.ndarray)
        y_data (np.ndarray)
        neurons_layout (list): List of integers indicates the number of neurons in each hidden layer.
        activation (str): Activation name. e.g., "relu", "linear"
        selected_bands (list): A list of integers indicates the desired bands.
        learning_rate (int)
        batch_size (int)
        valid_ratio (float): Validation size in terms of training data size.
        n_epochs (int)
        callbacks (list)
        save_path (str): Path for saving model

    Returns:
        str: The report for this model.
    """
    # Training with K-Fold Cross-Validation
    accuracy_hist = []
    k = 0
    kf = KFold(n_splits=n_splits)

    for train_idx, test_idx in kf.split(x_data):
        x_train, x_test = x_data[train_idx], x_data[test_idx]
        y_train, y_test = y_data[train_idx], y_data[test_idx]

        # Build models, loss function, and optimizer
        model = build_tf_model(
            neurons_layout=neurons_layout,
            activation=activation,
            selected_bands=selected_bands,
            learning_rate=learning_rate
        )

        print(model.summary())
        print(f"Start training with the {k+1}/{n_splits} fold.")

        history = model.fit(
            x_train, y_train,
            batch_size=batch_size,
            validation_split=valid_ratio,
            epochs=n_epochs,
            verbose=1,
            callbacks=callbacks
        )

        # Evaluation
        # print("\nRestoring the best weights...")
        # model.load_weights(save_path)
        print("Start evaluating...")
        scores = model.evaluate(x_test, y_test)

        # print(f"\nTesting loss = {scores[0]}")
        print(f"Testing accuracy = {scores[1]}")

        # utils.plot_loss_history(history)
        accuracy_hist.append(scores[1])
        k += 1

    mean_acc = round(np.mean(accuracy_hist) * 100, 2)
    std_acc = round(np.std(accuracy_hist) * 100, 2)

    report = f"Accuracy: {mean_acc}% ± {std_acc}% for {neurons_layout}"

    return report


def build_tf_model(
    neurons_layout: list,
    activation: str,
    selected_bands: list,
    learning_rate: float,
    objective='classification',
):
    """Construct model based on the parameters.

    Args:
        neurons_layout (list): A list of integers indicates the number of neurons in each layer.
        activation (str): Activation name. e.g., "relu", "linear"
        selected_bands (list): A list of integers indicates the desired bands.
        learning_rate (float)

    Returns:
        Tensorflow model class: Compiled model based on the parameter.
    """
    # Construct model
    model = Sequential()
    # Use original layout in the paper
    if neurons_layout == "original":
        model.add(Dense(256, activation=activation))
        model.add(Dense(256, activation=activation))
        model.add(Dense(256, activation=activation))
        # model.add(Dropout(0.3))
        model.add(Dense(256, activation=activation))
        # model.add(Dropout(0.3))
    else:
        for neurons in neurons_layout:
            model.add(Dense(neurons, activation=activation))

    # Adding output layer based on task
    if objective == 'classification':
        model.add(Dense(15))  # Output layer
        criterion = SparseCategoricalCrossentropy(from_logits=True)
        metric = ['accuracy']
    elif objective == 'regression':
        model.add(Dense(1, activation='linear'))
        criterion = MeanSquaredError()
        metric = ['mean_squared_error']

    model.build(input_shape=(None, len(selected_bands)))

    adam = keras.optimizers.Adam(lr=learning_rate)
    model.compile(optimizer=adam, loss=criterion, metrics=metric)
    print(model.summary())

    return model


def eval_mlp_regression(preds, mushroom_class, layout):
    mean_regression_scores = _mean_pred_per_class(preds, mushroom_class)

    ticks = [f"D{i}" for i in range(0, 30, 2)]
    if mushroom_class == "A":
        x_spaces = [i for i in range(0, 14)]
        ticks.pop(8)
    else:
        x_spaces = [i for i in range(0, 15)]

    plt.figure()
    plt.title(f"MLP freshness curve with {layout} on class {mushroom_class}.")
    plt.plot(x_spaces, mean_regression_scores, marker="o")
    plt.axhline(y=0.0, linestyle='--', color='r')
    plt.axhline(y=1.0, linestyle='--', color='r')
    plt.xlabel("Days")
    plt.ylabel("Freshness Decay Score")
    plt.ylim(-.2, 1.2)
    plt.xticks(x_spaces, ticks)
    # plt.savefig(f"./mlp_regr_origin_results_{mushroom_class}/{mushroom_class}_{layout}.png")
    plt.savefig(f"./regr_curves/{mushroom_class}_{layout}.png")


def _mean_pred_per_class(preds, mushroom_class):
    n_data_per_class = 50
    mean_regression_scores = []
    for i in range(0, len(preds), n_data_per_class):
        if mushroom_class == "A" and i == 400:
            continue
        mean_of_class = np.mean(preds[i:i+n_data_per_class])
        mean_regression_scores.append(mean_of_class)
    return mean_regression_scores

# SVR Functions


def build_SVR(kernel=None, gamma='auto', C=None):
    # Define scaler and SVR
    scaler = StandardScaler()
    svr = SVR(kernel=kernel, gamma=gamma, C=C)

    # Scale the trainig data by z-score (Normalization)
    model = Pipeline(steps=[("scaler", scaler), ("svr", svr)])
    return model


def eval_regression(mushroom_class, preds, model_id):
    '''Evaluate regression model'''
    mean_regression_scores = _mean_pred_per_class(preds, mushroom_class)

    plot_freshness_curve(mushroom_class, mean_regression_scores, model_id)


def plot_freshness_curve(mushroom_class, mean_regression_scores, model_id):
    ticks = [f"D{i}" for i in range(0, 30, 2)]
    if mushroom_class == "A":
        x_spaces = [i for i in range(0, 14)]
        ticks.pop(8)
    else:
        x_spaces = [i for i in range(0, 15)]
        
    plt.figure()
    plt.plot(x_spaces, mean_regression_scores, marker="o")
    plt.axhline(y=0.0, linestyle='--', color='r')
    plt.axhline(y=1.0, linestyle='--', color='r')
    plt.xlabel("Days")
    plt.ylabel("Freshness Decay Score")
    plt.ylim(-.2, 1.2)
    plt.xticks(x_spaces, ticks)
    plt.title(
        f"SVR freshness curve with {model_id} on class {mushroom_class}.")
    plt.savefig(
        f"./regr_curves/{mushroom_class}_{model_id}.png")


if __name__ == "__main__":
    opt = utils.Config()

    # print((neuron_permutor(1, 512, 32)))
    import os
    print(os.listdir(".\original_regr"))
