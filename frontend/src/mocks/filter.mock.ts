export const FILTERS_MOCK = [
  {
    "product": "yandex-go",
    "services": [
      {
        "service": "taxi-api",
        "environments": ["prod", "qa"]
      },
      {
        "service": "maps-api",
        "environments": ["prod", "preprod", "qa"]
      }
    ]
  },
  {
    "product": "yandex-market",
    "services": [
      {
        "service": "catalog-service",
        "environments": ["prod", "dev"]
      },
      {
        "service": "order-processing",
        "environments": ["qa"]
      }
    ]
  }
]