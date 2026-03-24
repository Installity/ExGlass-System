
# !!!!!!!!!!!!!!!CAUTION!!!!!!!!!!!!!!!!!!!!!!!!!!!CAUTION!!!!!!!!!!!!!!!!!!!!!!!!!!!
#------------------------------------------------------------------------------------
# WHEN ADDING NEW TRAINING DATA ALWAYS BE SURE TO CHANGE AMOUNT OF 'NUM_CLOSE' IMAGES
# AND NUM_SAFE IMAGES!!!!!!!!!!!!!!
#------------------------------------------------------------------------------------
# ALSO ALWAYS REMEMBER TO CHANGE NAME OF MODEL IN ORDER TO NOT OVERWRITE PAST MODELS.
#-------------------------------------------------------------------------------------
#                    ExGlass 2025 -- Tensorflow Training Program


#FOR ISE:
#This was my training pipeline. I used labelled images from the ESP32-CAM, applied augmentation to make the model less fragile, and trained a binary classifier to decide whether a scene was safe or close.




import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
import os

print("Current working directory:", os.getcwd())

# Set parameters
img_width, img_height = 320, 240  # Set resolution for all training data
batch_size = 32  
epochs = 60       

# Create an ImageDataGenerator for data augmentation and normalization
datagen = ImageDataGenerator(
    rescale=1.0/255,           # Normalize pixel values to [0,1]
    validation_split=0.2,      # Use 20% of images for validation
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    horizontal_flip=True,
    brightness_range=[0.8, 1.2]  # vary brightness to improve generalization
)


#data_dir = nuh uh (...\DataTraining)

# Create training and validation generators
train_generator = datagen.flow_from_directory(
    data_dir,
    target_size=(img_height, img_width),  
    batch_size=batch_size,
    class_mode='binary',   # For binary classification ("close" vs "safe")
    subset='training'
)

validation_generator = datagen.flow_from_directory(
    data_dir,
    target_size=(img_height, img_width),
    batch_size=batch_size,
    class_mode='binary',
    subset='validation'
)

print("Class indices:", train_generator.class_indices)
#{'close': 0, 'safe': 1}

# CAUTION !!!!!!!!!!!! CAUTION !!!!!!!!!!!
# ALWAYS UPDATE THESE NUMBERS BELOW WHENEVER ADDING
# NEW TRAINING DATA
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
num_close = 1785
num_safe = 1544
total_samples = num_close + num_safe  # 3329 total images (3/26/25)
num_classes = 2

# Calculate class weights using: weight = total_samples / (num_classes * count)
weight_close = total_samples / (num_classes * num_close)  # For class 'close' (index 0)
weight_safe  = total_samples / (num_classes * num_safe)   # For class 'safe' (index 1)
class_weights = {0: weight_close, 1: weight_safe}
print("Class weights:", class_weights)

# Build a CNN model for binary classification
model = Sequential([
    Conv2D(32, (3, 3), activation='relu', input_shape=(img_height, img_width, 3)),
    MaxPooling2D(2, 2),
    Conv2D(64, (3, 3), activation='relu'),
    MaxPooling2D(2, 2),
    Flatten(),
    Dense(128, activation='relu'),
    Dropout(0.5),
    Dense(1, activation='sigmoid')  # Sigmoid for the binary classification
])

model.compile(optimizer=Adam(learning_rate=1e-4), loss='binary_crossentropy', metrics=['accuracy'])
model.summary()

# callbacks: EarlyStopping, ModelCheckpoint, and ReduceLROnPlateau (reducing learning rate when metric plateaus)
early_stopping = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
checkpoint = ModelCheckpoint('obstacle_detectorv6_best.h5', monitor='val_loss', save_best_only=True)
reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, min_lr=1e-6, verbose=1)

# Model Training begins
history = model.fit(
    train_generator,
    epochs=epochs,
    validation_data=validation_generator,
    callbacks=[early_stopping, checkpoint, reduce_lr],
    class_weight=class_weights
)

# Save the final trained model
model.save('obstacle_detectorv6.h5') #ALREADY UPDATED FOR 3/27/25
