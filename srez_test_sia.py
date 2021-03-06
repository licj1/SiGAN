import srez_demo
import srez_input_y
import srez_model_sia
import srez_train
import operator
import os.path
import random
import numpy as np
import numpy.random
import pdb
import random as rn
import scipy.misc
import os.path
import tensorflow as tf
import sys

FLAGS = tf.app.flags.FLAGS

# Configuration (alphabetically)
tf.app.flags.DEFINE_integer('batch_size', 500, "Number of samples per batch.")
tf.app.flags.DEFINE_string('checkpoint_dir', 'checkpoint', "Output folder where checkpoints are dumped.")
tf.app.flags.DEFINE_integer('checkpoint_period', 10000, "Number of batches in between checkpoints")
tf.app.flags.DEFINE_string('dataset', 'dataset', "Path to the dataset directory.")
tf.app.flags.DEFINE_float('epsilon', 1e-8, "Fuzz term to avoid numerical instability")
tf.app.flags.DEFINE_float('wei_lab', 1, "Weight for label information")
tf.app.flags.DEFINE_string('run', 'demo', "Which operation to run. [demo|train]")
tf.app.flags.DEFINE_float('gene_l1_factor', 0.7, "Multiplier for generator L1 loss term")
tf.app.flags.DEFINE_float('learning_beta1', 0.5, "Beta1 parameter used for AdamOptimizer")
tf.app.flags.DEFINE_float('learning_rate_start', 0.00020, "Starting learning rate used for AdamOptimizer")
tf.app.flags.DEFINE_integer('learning_rate_half_life', 5000, "Number of batches until learning rate is halved")
tf.app.flags.DEFINE_bool('log_device_placement', False, "Log the device where variables are placed.")
tf.app.flags.DEFINE_bool('LargeG', True, "Log the device where variables are placed.")
tf.app.flags.DEFINE_integer('num_ID', 500, "How much the labels will be test...")
tf.app.flags.DEFINE_integer('sample_size', 64, "Image sample size in pixels. Range [64,128]")
tf.app.flags.DEFINE_integer('summary_period', 1000,"Number of batches between summary data dumps")
tf.app.flags.DEFINE_integer('random_seed', 0, "Seed used to initialize rng.")
tf.app.flags.DEFINE_integer('test_vectors', 16,  """Number of features to use for testing""")
tf.app.flags.DEFINE_string('train_dir', 'train', "Output folder where training logs are dumped.")
tf.app.flags.DEFINE_string('test_dir', 'test', "Output folder where training logs are dumped.")
tf.app.flags.DEFINE_string('HRLR_dir', 'LR_HR', "Output folder where training logs are dumped.")                     
tf.app.flags.DEFINE_string('training_img_dir', '../SREZ_Data/', "Output folder where training logs are dumped.")
tf.app.flags.DEFINE_string('testing_img_dir', '../SREZ_Data/list.txt', "Output folder where training logs are dumped.")
tf.app.flags.DEFINE_string('txt', 'list.txt', "Output folder where training logs are dumped.")
tf.app.flags.DEFINE_integer('train_time', 2000,  "Time in minutes to train the model")
tf.app.flags.DEFINE_integer('init_layer_size', 512, "Seed used to initialize rng.")
tf.app.flags.DEFINE_bool('useRecTerm', True,  "Set whether the reconstruction term is used or not")

label=[]
def prepare_dirs(delete_train_dir=False):
    # Create checkpoint dir (do not delete anything)
    if not tf.gfile.Exists(FLAGS.checkpoint_dir):
        tf.gfile.MakeDirs(FLAGS.checkpoint_dir)
    
    # Cleanup train dir
    if delete_train_dir:
        if tf.gfile.Exists(FLAGS.train_dir):
            tf.gfile.DeleteRecursively(FLAGS.train_dir)
        tf.gfile.MakeDirs(FLAGS.train_dir)

    # Return names of training files
    if not tf.gfile.Exists(FLAGS.dataset) or \
       not tf.gfile.IsDirectory(FLAGS.dataset):
        raise FileNotFoundError("Could not find folder `%s'" % (FLAGS.dataset,))

    fn=FLAGS.training_img_dir
    fn2=FLAGS.testing_img_dir

    return FLAGS.training_img_dir


def setup_tensorflow():
    # Create session
    config = tf.ConfigProto(log_device_placement=FLAGS.log_device_placement)
    config.gpu_options.allow_growth = True
    sess = tf.Session(config=config)

    # Initialize rng with a deterministic seed
    with sess.graph.as_default():
        tf.set_random_seed(FLAGS.random_seed)
        
    random.seed(FLAGS.random_seed)
    np.random.seed(FLAGS.random_seed)

    summary_writer = tf.summary.FileWriter(FLAGS.train_dir, sess.graph)

    return sess, summary_writer

def _demo():
	    
    LRsize = 16
    HRsize = LRsize*4
    # Load checkpoint
    if not tf.gfile.IsDirectory(FLAGS.checkpoint_dir):
        raise FileNotFoundError("Could not find folder `%s'" % (FLAGS.checkpoint_dir,))

    # Setup global tensorflow state
    sess, summary_writer = setup_tensorflow()

    # Prepare directories
    with open(FLAGS.training_img_dir+FLAGS.txt) as fn:
        dx = fn.readlines()	
    len1 = len(dx)

    FLAGS.batch_size=len1
    test_features,  test_labels, _,fn = srez_input_y.setup_inputs(sess,  FLAGS.training_img_dir+FLAGS.txt, image_size=HRsize, crop_size=97, isTest=True) # image_size 128 for CASIA , 97 for LFW
    FLAGS.batch_size=10
    
    test_feature, test_label ,fn= sess.run([test_features, test_labels,fn])
    s1 = test_feature.shape
    print(s1)
    tid = FLAGS.num_ID
    

            
    # Create and initialize model
    fea1 = tf.placeholder(tf.float32, shape=[None, LRsize,LRsize,3])
    lab1 = tf.placeholder(tf.float32,shape=[None, HRsize,HRsize,3])
    [gene_minput, gene_moutput,
     gene_output, gene_var_list,
    disc_real_output, disc_fake_output, disc_var_list, 
    gene_minput2, gene_moutput2,
     gene_output2, gene_var_list2,
    disc_real_output2, disc_fake_output2, disc_var_list2,
    feat1, feat2] = srez_model_sia.create_model(sess, fea1, lab1, fea1, lab1, False)

    # Restore variables from checkpoint
    saver = tf.train.Saver()
    filename = 'checkpoint_new.txt'
    filename = os.path.join(FLAGS.checkpoint_dir, filename)
    saver.restore(sess, filename)
    td = TrainData(locals())

    # Execute demo
    gout = []
    fnn=[]
    HR=[]
    LR=[]
    didx=[]
    bs = 10
    channels=3
    
    for k in range(0,s1[0]+bs,bs):
        if k+bs>s1[0]:
             st=range(k,s1[0])
             st=np.asarray(st)
             st=np.concatenate((st,np.zeros(bs-len(st)) ), axis=0 )
             st=np.asarray(st,dtype=int)
        else:
            st = range(k, k+bs)
         #~ pdb.set_trace()
        aa=td.sess.run(td.gene_moutput, feed_dict = {td.gene_minput: test_feature[st,:,:,:]})
        fnn.append(fn[st])
        HR.append(test_label[st,:,:,:])
        LR.append(test_feature[st,:,:,:])
            
        gout.append(np.reshape(np.asarray(aa), [-1, HRsize,HRsize, 3]))
            
        if (k>1) & ((k%bs==0) | ((k+1)==s1[0])):
            output(gout, LR, HR, fnn, td, HRsize, LRsize)
            gout=[]
            LR=[]
            HR=[]
            fnn=[]
                
            
            
        if (k%(s1[0]/100)<1):
            sys.stdout.write('|')
            sys.stdout.flush()

    
def output(gout, test_feature, test_label, fn, td, HRsize, LRsize):
	
    vlen= len(gout)
    size = HRsize,HRsize
    #~ pdb.set_trace()
    test_feature=np.reshape(np.asarray(test_feature), [-1, LRsize, LRsize, 3 ])
    test_label=np.reshape(np.asarray(test_label), [-1, HRsize,HRsize,3])
    clipped = np.reshape(np.asarray(gout), [-1, HRsize,HRsize, 3]) 
    fn=np.reshape(fn,[-1])
    #~ image=clipped/np.max(clipped)
    
    NN = tf.image.resize_nearest_neighbor(test_feature, size)
    NN = tf.maximum(tf.minimum(NN, 1.0), 0.0)
    NN = td.sess.run(NN)

    bicubic = tf.image.resize_bicubic(test_feature, size)
    bicubic = tf.maximum(tf.minimum(bicubic, 1.0), 0.0)
    bicubic = td.sess.run(bicubic)
    
    hr= tf.maximum(tf.minimum(test_label, 1.0), 0.0)
    hr = td.sess.run(hr)
    combo   = tf.cast(tf.concat( [NN, bicubic,clipped, hr], 2), tf.float32)
    combo = td.sess.run(combo)
    
    testdir = FLAGS.checkpoint_dir+FLAGS.test_dir
    if not os.path.exists(FLAGS.HRLR_dir):
        os.makedirs(FLAGS.HRLR_dir) 
    if not os.path.exists(testdir):
        os.makedirs(testdir) 
    
    for i in range(len(fn)):
        #~ pdb.set_trace()
        #~ fx=str(fn[i]).split('/')
        #~ t1=len(fx)
        #~ fx=fx[t1-2]+"-"+fx[t1-1]
        #~ filename = '%s.png' % (fx)
        
        filename=os.path.basename(str(fn[i]))
        filename=filename.replace("'","")
        print(filename)
        fx=filename
        recFN = os.path.join(testdir, filename)
        scipy.misc.toimage(clipped[i,:,:,0:3], cmin=0., cmax=1.).save(recFN)
        BIFN = os.path.join(FLAGS.HRLR_dir, 'Bicubic-%s.png' % (fx))
        LRFN = os.path.join(FLAGS.HRLR_dir, 'LR-%s.png' % (fx))
        HRFN = os.path.join(FLAGS.HRLR_dir, 'HR-%s.png' % (fx))
        Combo2 = os.path.join(FLAGS.HRLR_dir, 'Combo-%s.png' % (fx))
        scipy.misc.toimage(bicubic[i,:,:,:], cmin=0., cmax=1.).save(BIFN)
        scipy.misc.toimage(NN[i,:,:,:], cmin=0., cmax=1.).save(LRFN)
        scipy.misc.toimage(hr[i,:,:,:], cmin=0., cmax=1.).save(HRFN)
        scipy.misc.toimage(combo[i,:,:,:], cmin=0., cmax=1.).save(Combo2)
    print("Saved %d imagees to %s!!" % (len(fn), FLAGS.test_dir))

class TrainData(object):
    def __init__(self, dictionary):
        self.__dict__.update(dictionary)
        

def main(argv=None):
    # Training or showing off?

    if FLAGS.run == 'demo':
        _demo()
    elif FLAGS.run == 'train':
        _train()

if __name__ == '__main__':
  tf.app.run()
