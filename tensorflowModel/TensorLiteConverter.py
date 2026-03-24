#FOR ISE:
#I converted the trained model to TensorFlow Lite because it was lighter and easier to deploy for live inference.

import tensorflow as tf

#IMPORTANT!!!!!!!! REMEMBER TO CHANGE NAMES OF MODEL VERSION WHEN UPDATING

# Load the trained model
model = tf.keras.models.load_model('obstacle_detectorv6.h5')

# Convert model to TFLite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

# save
with open('obstacle_detector_v6.tflite', 'wb') as f:
    f.write(tflite_model)

print("TFLite model conversion complete.")
