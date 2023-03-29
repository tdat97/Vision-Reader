from pypylon import pylon      
import cv2

class BaslerCam():
    def __init__(self, ExposureTime=25000, logger=None, gray_scale=False):
        # conecting to the first available camera
        self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

        # Grabing Continusely (video) with minimal delay
        self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly) 
        self.converter = pylon.ImageFormatConverter()

        # converting to opencv bgr format
        if gray_scale:
            self.converter.OutputPixelFormat = pylon.PixelType_Mono8
        else:
            self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

        # settimg ExposureTime
        self.camera.ExposureTime.SetValue(ExposureTime)
        
        if logger is not None:
            logger.info(f"Camera Name : {self.camera.GetDeviceInfo().GetModelName()}")
            logger.info(f"Exposure Time : {self.camera.ExposureTime.GetValue()}")
            logger.info(f"DeviceLinkThroughputLimit : {self.camera.DeviceLinkThroughputLimit.GetValue()}")

    def get_image(self):
        image = None
        if self.camera.IsGrabbing():
            grabResult = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if grabResult.GrabSucceeded():
                # Access the image data
                image = self.converter.Convert(grabResult)
                image = image.GetArray()
            grabResult.Release()
        return image

    def set_exposure(self, value):
        assert type(value) == int and 100 <= value <= 50000
        self.camera.ExposureTime.SetValue(value)

    def close(self):
        self.camera.StopGrabbing()
        
        
        
        
if __name__ == "__main__":
    import os
    cam = SentechCam(ExposureTime=25000, gray_scale=True)
    n = len(os.listdir("./images"))
    for i in range(n, 5000):
        img = cam.get_image()
        cv2.imwrite(f"./images/{i:04d}.png", img)
        cv2.imshow('test', img)
        if cv2.waitKey(1000*300) == ord('q'): break
    cv2.destroyAllWindows()
