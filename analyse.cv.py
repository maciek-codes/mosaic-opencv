import numpy as np
import cv2
import cv

from azure.storage import QueueService
from azure.storage import BlobService
from azure.storage import TableService

from base64 import b64decode
import itertools
from time import sleep

def blobToOpenCV(blob):
    arr = np.asarray(bytearray(blob), dtype=np.uint8)
    img = cv2.imdecode(arr, -1)
    return img

# Analyse the overall colour of image
def getCharacteristics( image ):
  # range_hist = [0, 100, -100, 100, -100, 100]
  # hist_1 = cv2.calcHist([image], [0, 1, 2], None, [20, 20, 20], range_hist)
  hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
  h = hsv[:,:,0]
  s = hsv[:,:,1]
  v = hsv[:,:,2]

  hs = list(itertools.chain.from_iterable(h.tolist()))
  ss = list(itertools.chain.from_iterable(s.tolist()))
  vs = list(itertools.chain.from_iterable(v.tolist()))

  counts = np.bincount(hs)
  hw = np.argmax(counts)

  counts = np.bincount(ss)
  sw = np.argmax(counts)

  counts = np.bincount(vs)
  vw = np.argmax(counts)

  return (int(hw), int(sw), int(vw))

# Constants
blob_container = 'imagecontainer'
imagesQueue = 'imagesqueue'

tableName = 'photos'
tablePartitionKey = 'allphotos'

# Get queue credentials
# accountName = environ["AZURE_STORAGE_ACCOUNT"]
with open ("ASA.key", "r") as myfile:
  accountName=myfile.read().replace('\n', '')
# accountKey = environ["AZURE_STORAGE_ACCESS_KEY"]
with open ("ASK.key", "r") as myfile:
  accountKey=myfile.read().replace('\n', '')

# Create blob service
blob_service = BlobService( account_name=accountName, account_key=accountKey )
blob_service.create_container( blob_container )

# Open queue with given credentials
queue_service = QueueService( account_name=accountName, account_key=accountKey )

# Open table service
table_service = TableService( account_name=accountName, account_key=accountKey )

# Repeat
while(True):

  # get images form *imagesQueue* - it is invoked by CRON
  messages = queue_service.get_messages( imagesQueue )
  for message in messages:
    # get image: image ID
    imgBlobName = b64decode( message.message_text )
    print( imgBlobName )
    tableRowKey = imgBlobName
    blob = blob_service.get_blob(blob_container, imgBlobName)
    image = blobToOpenCV(blob)
    # process image
    (hw, sw, vw) = getCharacteristics( image )

    # {'PartitionKey': 'allPhotos', 'RowKey': 'imageName', 'thumbnail' : 'thumbnailName',
    #  'userId' : ?, 'local' : ?, 'hue' : 200, 'saturation' : 200, 'value' : 200}
    ## query for image in table to ensure existence
    currentTask = table_service.get_entity( tableName, tablePartitionKey, tableRowKey)
  
    ## send the quantities to table: save thumbnail ID & save image characteristics
    # currentTask.thumbnail = tnID
    currentTask.hue = hw
    currentTask.saturation = sw
    currentTask.value = vw
    table_service.update_entity( tableName, tablePartitionKey, tableRowKey, currentTask)

    # dequeue image
    queue_service.delete_message( imagesQueue, message.message_id, message.pop_receipt )
    sleep(15)



# Get the mosaic image from some queue


## Divide on quadrants and analyse each quadrant ? concurrently
## Wait until table is filled with values - no NILLs - thumbnails done
## Send request for image with given statistics
## Receive thumbnail and paste it
## REPEAT

# Save the file to blob

# Send DONE notification

