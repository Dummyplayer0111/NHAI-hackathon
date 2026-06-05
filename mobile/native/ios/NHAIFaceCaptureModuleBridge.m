#import <React/RCTBridgeModule.h>

@interface RCT_EXTERN_MODULE(NHAIFaceCapture, NSObject)

RCT_EXTERN_METHOD(captureFaceSample:(NSDictionary *)options
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

@end
