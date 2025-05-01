import os
import tensorflow as tf
import argparse

def convert_pb_to_savedmodel(pb_path, output_dir='saved_model'):
    """Convert a frozen .pb model to TensorFlow SavedModel format."""
    print(f"Converting {pb_path} to SavedModel format in {output_dir}")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Import the graph
    with tf.io.gfile.GFile(pb_path, 'rb') as f:
        graph_def = tf.compat.v1.GraphDef()
        graph_def.ParseFromString(f.read())
    
    # Create a new graph and import the GraphDef
    with tf.compat.v1.Session(graph=tf.Graph()) as sess:
        # Import the graph
        tf.import_graph_def(graph_def, name='')
        
        # Get input and output tensors
        graph = tf.compat.v1.get_default_graph()
        input_tensor = graph.get_tensor_by_name('input:0')
        output_tensor = graph.get_tensor_by_name('output:0')
        
        # Create a SavedModel builder
        builder = tf.compat.v1.saved_model.builder.SavedModelBuilder(output_dir)
        
        # Define input and output signature
        tensor_info_input = tf.compat.v1.saved_model.utils.build_tensor_info(input_tensor)
        tensor_info_output = tf.compat.v1.saved_model.utils.build_tensor_info(output_tensor)
        
        # Build the signature definition
        signature_definition = tf.compat.v1.saved_model.signature_def_utils.build_signature_def(
            inputs={'input': tensor_info_input},
            outputs={'output': tensor_info_output},
            method_name=tf.compat.v1.saved_model.signature_constants.PREDICT_METHOD_NAME
        )
        
        # Add the signature definition to the builder
        builder.add_meta_graph_and_variables(
            sess,
            [tf.compat.v1.saved_model.tag_constants.SERVING],
            signature_def_map={
                tf.compat.v1.saved_model.signature_constants.DEFAULT_SERVING_SIGNATURE_DEF_KEY: signature_definition
            }
        )
        
        # Save the model
        builder.save()
        print(f"SavedModel successfully created at {output_dir}")
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert .pb file to SavedModel format')
    parser.add_argument('--pb_path', type=str, required=True, help='Path to frozen .pb model')
    parser.add_argument('--output_dir', type=str, default='saved_model', help='Output directory for SavedModel')
    
    args = parser.parse_args()
    convert_pb_to_savedmodel(args.pb_path, args.output_dir)
