#IMAGE PROCESSING LIBRARIES
import cv2
from PIL import Image
import imutils #used to resize the obtained framefrom skimage.filters import threshold_local #Compute a threshold mask image based on local pixel neighborhood
import os #traverse directory
import time
import numpy as np
#Pyserial Library - create serial connection to arduino port
import serial
#Google text-to-speech
from gtts import gTTS 
#TESSERACT-OCR 
import pytesseract

#-------------------------------------------#
#ARDUINO CONNECTION
Arduinouno_Serial = serial.Serial('COM4',9600) #opens serial port
print(Arduinouno_Serial.readline()) # read a '\n' terminated line
#OCR PATH
pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files (x86)/Tesseract-OCR/tesseract' #location of pytesseract database
#-------------------------------------------#
#FUNCTIONS
def order_points(pts):
	# initialize a list of coordinates that will be ordered
	# such that the first entry in the list is the top-left,
	# the second entry is the top-right, the third is the
	# bottom-right, and the fourth is the bottom-left
	rect = np.zeros((4, 2), dtype = "float32")
 
	# the top-left point will have the smallest sum, whereas
	# the bottom-right point will have the largest sum
	s = pts.sum(axis = 1)
	rect[2] = pts[np.argmax(s)]
	rect[0] = pts[np.argmin(s)]
	
 
	# now, compute the difference between the points, the
	# top-right point will have the smallest difference,
	# whereas the bottom-left will have the largest difference
	diff = np.diff(pts, axis = 1)
	rect[3] = pts[np.argmax(diff)]
	rect[1] = pts[np.argmin(diff)]
	
 
	# return the ordered coordinates
	return rect

def four_point_transform(image, pts):
	# obtain a consistent order of the points and unpack them
	# individually
	rect = order_points(pts)
	(tl, tr, br, bl) = rect
 
	# compute the width of the new image, which will be the
	# maximum distance between bottom-right and bottom-left
	# x-coordiates or the top-right and top-left x-coordinates
	widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
	widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
	maxWidth = max(int(widthA), int(widthB))
 
	# compute the height of the new image, which will be the
	# maximum distance between the top-right and bottom-right
	# y-coordinates or the top-left and bottom-left y-coordinates
	heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
	heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
	maxHeight = max(int(heightA), int(heightB))
 
	# now that we have the dimensions of the new image, construct
	# the set of destination points to obtain a "birds eye view",
	# (i.e. top-down view) of the image, again specifying points
	# in the top-left, top-right, bottom-right, and bottom-left
	# order
	dst = np.array([
		[0, 0],
		[maxWidth - 1, 0],
		[maxWidth - 1, maxHeight - 1],
		[0, maxHeight - 1]], dtype = "float32")
 
	# compute the perspective transform matrix and then apply it
	M = cv2.getPerspectiveTransform(rect, dst)
	warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
 
	# return the warped image
	return warped

def get_string(img_path):
    # Read image with opencv
    img = cv2.imread(img_path)

    # Convert to gray
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # filtering the image
    
    img = cv2.bilateralFilter(img,10,10,6)
    
    #ret,img = cv2.threshold(img,127,255,cv2.THRESH_BINARY)
    #img = cv2.threshold(img, 0, 255,cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    #img = cv2.medianBlur(img, 3)

    # Apply dilation and erosion to remove some noise
    kernel = np.ones((1, 1), np.uint8)
    img = cv2.dilate(img, kernel, iterations=1)
    img = cv2.erode(img, kernel, iterations=1)
    # img = cv2.resize(img,(100,100), interpolation = cv2.INTER_AREA)

    # Write image after removed noise
    cv2.imwrite("removed_noise.png", img)

    #  Apply threshold to get image with only black and white
    # img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)

    # Write the image after apply opencv to do some ...
    cv2.imwrite(img_path, img)
     # Recognize text with tesseract for python
    result = pytesseract.image_to_string(Image.open(img_path))
    #result is the string to be taken by gTTS
    # Remove template file
    #os.remove(temp)
    
    # print(type(result))
    
    for i in range(len(result)): #for Serial transmission of data to arduino
        

        Arduinouno_Serial.write(result[i].encode())
        print(result[i])
	        time.sleep(2)

    return result
#-------------------------------------------#

cap = cv2.VideoCapture(0) 
#cv2.VideoCapture(1) #for external camera
image_path = "img.jpg"

while True:
    #finding edges
    sec = time.time() #returns current time
    ret, frame = cap.read() #reads frame by frame input
    ratio = frame.shape[0]/500.0
    orig = frame.copy()
    frame = imutils.resize(frame, height = 500)
    frame = cv2.bilateralFilter(frame,10,10,6)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray,10,10,6)
    gray = cv2.GaussianBlur(gray, (5,5), 0)
    edged = cv2.Canny(gray, 75, 200)
    # finding the contours
    _, cnts, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key = cv2.contourArea, reverse = True)[:5]
    
    for c in cnts: #contours
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02*peri, True)
        
        # if our approximated contour have 4 points then we assume that we have founded our screen
        if len(approx) == 4:
            screenCnt = approx
            cv2.drawContours(frame, [screenCnt], -1, (0,255,0), 3)
            
            # apply a prespective Transform & Threshold
            wrapped = four_point_transform(orig, screenCnt.reshape(4, 2) * ratio)
            wrapped = cv2.cvtColor(wrapped, cv2.COLOR_BGR2GRAY)
            T = threshold_local(wrapped, 11, offset = 10, method = "gaussian")
            wrapped = (wrapped > T).astype("uint8")*255
            
            cv2.imshow("scanned", imutils.resize(wrapped, height = 650))
            #time.sleep(1)
            #if count == 10000:
            #    cv2.imwrite(image_path, wrapped)
            #    break
    
    cv2.imshow("frame", frame)
    
    if cv2.waitKey(1) == 27:
        cv2.imwrite("img.jpg", wrapped)
        break

cap.release()    
cv2.destroyAllWindows()

filename = "123.jpg" #location where image captured from camera is saved

print('--- Started recognizing text from image ---')
mytext = get_string(filename)
print(mytext)
language = 'en'
myobj = gTTS(text=mytext, lang=language, slow=False)
myobj.save("output.mp3")
os.system("start output.mp3")
print("Process Completed")
