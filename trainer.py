# Custom Modules
import utils

# Numeric Operations
import numpy as np

# Sci-Kit Learn
from sklearn.model_selection import KFold

# Tensorflow
from tensorflow import keras
from keras.models import Sequential
from keras.layers import Dense
from keras.losses import SparseCategoricalCrossentropy


def neuron_permutor(n_hidden: int, max_neuron='auto', min_neuron=32) -> list:
    """Return the permutation of number of nuerons for a neural network.

    Args:
        n_hidden (int): Number of hidden layers.
        max_neuron (int, optional): Max number of neurons. Defaults to 256.
        min_neuron (int, optional): Min number of neurons. Defaults to 32.

    Returns:
        list: A list of permutation.
    """
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


def build_model(neurons_layout: list, activation: str, selected_bands: list, learning_rate: float):
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

    for neurons in neurons_layout:
        model.add(Dense(neurons, activation=activation))

    model.add(Dense(15))  # Output

    model.build(input_shape=(None, len(selected_bands)))

    adam = keras.optimizers.Adam(lr=learning_rate)
    criterion = SparseCategoricalCrossentropy(from_logits=True)
    model.compile(optimizer=adam, loss=criterion, metrics=['accuracy'])

    return model


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
        model = build_model(
            neurons_layout=neurons_layout,
            activation=activation,
            selected_bands=selected_bands,
            learning_rate=learning_rate
        )

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


if __name__ == "__main__":
    opt = utils.Config()

    print((neuron_permutor(1, 512, 32)))
