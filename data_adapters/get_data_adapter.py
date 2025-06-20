
def get_data_adapter(is_offline: bool = False):
    if is_offline:
        from data_adapters.offline_adapter import OfflineAdapter
        return OfflineAdapter()
    else:
        from data_adapters.azure_sql_adapter import AzureSQLAdapter
        return AzureSQLAdapter()

# EOF
