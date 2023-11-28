from pydantic import BaseModel


class VideoInfo(BaseModel):
    name: str
    link: str
    id: str
    size: int


# "[{\"name\":\"722686551.245434_岡林 弘晃 1.mp4\",
# \"link\":\"https://nsengi.sharepoint.com/sites/app274/Shared%20Documents/%E3%82%A2%E3%83%97%E3%83%AA/Microsoft%20Forms/%E7%B0%A1%E5%8D%98%E8%A6%81%E7%B4%84/%E8%B3%AA%E5%95%8F/722686551.245434_%E5%B2%A1%E6%9E%97%20%E5%BC%98%E6%99%83%201.mp4\",
# \"id\":\"01ZY2E7JGCA2U7FXNFCJHZNNLVEYQJ25BZ\",
# \"type\":null,
# \"size\":14174415,
# \"referenceId\":\"01ZY2E7JGEZOMAAHO3HJC3ZEZELJRRF3JX\",
# \"driveId\":\"b!V60RShUsikuzHnQsz43TkJ-eRTSpvEVCjJroakE-0tQeO6UzQC3oSb1Rhvzx8hcG\",
# \"status\":1,
# \"uploadSessionUrl\":null}]"
